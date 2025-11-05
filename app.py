from pathlib import Path
import sqlite3
from datetime import datetime, date
import io
import base64
import urllib.parse as urlparse

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    send_file,
    flash,
    session,
)
import os
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from flask_wtf import CSRFProtect
import pandas as pd
import matplotlib.pyplot as plt

APP_DIR = Path(__file__).parent
DB_PATH = APP_DIR / "expenses.db"

# Database configuration - PostgreSQL for production, SQLite for local
DATABASE_URL = os.environ.get('DATABASE_URL')
USE_POSTGRES = DATABASE_URL is not None

if USE_POSTGRES:
    import psycopg2
    import psycopg2.extras

CATEGORIES = [
    "Rent",
    "Utilities: Electricity",
    "Utilities: Water",
    "Utilities: Internet",
    "Food: Groceries",
    "Food: Meat",
    "Food: Eating Out / Wolt",
    "Sport",
    "Household / Cleaning",
    "Transport",
    "Health / Beauty",
    "Gifts / Events",
    "שונות ומשונות",
    "Arnoni",
    "School Expenses",
]
# Household configuration - maps users to their household groups
HOUSEHOLD_USERS = {
    "erez_lia": ["Erez", "Lia"],
    "parents": ["mom", "dad"]
}

# User to household mapping for quick lookup
USER_HOUSEHOLD = {}
for household, users in HOUSEHOLD_USERS.items():
    for user in users:
        USER_HOUSEHOLD[user] = household

# Keep these as backend constants for now, but they could be made configurable
DEFAULT_PEOPLE = ["erez", "lia"]  # This will be dynamic based on user's household

# Budget limits per person per category (in ₪)
# Note: Keep case consistent with authentication usernames
BUDGET_LIMITS = {
    "Erez": {
        "Food: Groceries": 500,
        "Food: Meat": 300,
        "Food: Eating Out / Wolt": 400,
        "Transport": 20,
        "Health / Beauty": 240,
        "Sport": 420,
        "Household / Cleaning": 100,
        "Gifts / Events": 200,
    },
    "Lia": {
        "Food: Groceries": 500,
        "Food: Meat": 300,
        "Food: Eating Out / Wolt": 400,
        "Transport": 20,
        "Health / Beauty": 240,
        "Sport": 420,
        "Household / Cleaning": 100,
        "Gifts / Events": 200,
    },
    "mom": {
        "Food: Groceries": 600,
        "Food: Meat": 200,
        "Food: Eating Out / Wolt": 300,
        "Transport": 50,
        "Health / Beauty": 150,
        "Sport": 100,
        "Household / Cleaning": 200,
        "Gifts / Events": 150,
    },
    "dad": {
        "Food: Groceries": 400,
        "Food: Meat": 300,
        "Food: Eating Out / Wolt": 250,
        "Transport": 100,
        "Health / Beauty": 100,
        "Sport": 200,
        "Household / Cleaning": 100,
        "Gifts / Events": 100,
    }
}


def init_db():
    if USE_POSTGRES:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS expenses (
                id SERIAL PRIMARY KEY,
                ts TIMESTAMP NOT NULL,
                tx_date DATE NOT NULL,
                category TEXT NOT NULL,
                amount DECIMAL(10,2) NOT NULL,
                payer TEXT NOT NULL,
                notes TEXT,
                split_with TEXT DEFAULT NULL,
                household TEXT DEFAULT 'default'
            )
            """
        )
        # Create user_budgets table for persistent budget storage
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS user_budgets (
                id SERIAL PRIMARY KEY,
                username TEXT NOT NULL,
                category TEXT NOT NULL,
                budget_limit DECIMAL(10,2) NOT NULL,
                household TEXT DEFAULT 'default',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(username, category, household)
            )
            """
        )
        conn.commit()
        conn.close()
    else:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts TEXT NOT NULL,
                tx_date TEXT NOT NULL,
                category TEXT NOT NULL,
                amount REAL NOT NULL,
                payer TEXT NOT NULL,
                notes TEXT,
                split_with TEXT DEFAULT NULL,
                household TEXT DEFAULT 'default'
            )
            """
        )
        # Create user_budgets table for persistent budget storage
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS user_budgets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                category TEXT NOT NULL,
                budget_limit REAL NOT NULL,
                household TEXT DEFAULT 'default',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(username, category, household)
            )
            """
        )
        conn.commit()
        conn.close()


def get_conn():
    if USE_POSTGRES:
        print(f"DEBUG: Using PostgreSQL database: {DATABASE_URL[:30]}...")
        return psycopg2.connect(DATABASE_URL)
    else:
        print(f"DEBUG: Using SQLite database: {DB_PATH}")
        return sqlite3.connect(DB_PATH)


def migrate_db():
    """Add migrations for split_with and household columns if they don't exist"""
    try:
        conn = get_conn()
        cur = conn.cursor()
        if USE_POSTGRES:
            cur.execute("ALTER TABLE expenses ADD COLUMN IF NOT EXISTS split_with TEXT DEFAULT NULL")
            cur.execute("ALTER TABLE expenses ADD COLUMN IF NOT EXISTS household TEXT DEFAULT 'default'")
            cur.execute("ALTER TABLE user_budgets ADD COLUMN IF NOT EXISTS household TEXT DEFAULT 'default'")
        else:
            # Check if columns exist for SQLite
            cur.execute("PRAGMA table_info(expenses)")
            columns = [row[1] for row in cur.fetchall()]
            if 'split_with' not in columns:
                cur.execute("ALTER TABLE expenses ADD COLUMN split_with TEXT DEFAULT NULL")
            if 'household' not in columns:
                cur.execute("ALTER TABLE expenses ADD COLUMN household TEXT DEFAULT 'default'")
                
            # Check user_budgets table
            cur.execute("PRAGMA table_info(user_budgets)")
            budget_columns = [row[1] for row in cur.fetchall()]
            if 'household' not in budget_columns:
                cur.execute("ALTER TABLE user_budgets ADD COLUMN household TEXT DEFAULT 'default'")
        conn.commit()
        conn.close()
        print("Database migration completed successfully")
    except Exception as e:
        print(f"Migration warning: {e}")


def get_user_household(username):
    """Get the household for a given user with case-insensitive matching and production fallback"""
    if not username:
        print("WARNING: get_user_household called with empty username")
        return "default"
    
    try:
        # Try exact match first
        if username in USER_HOUSEHOLD:
            return USER_HOUSEHOLD[username]
        
        # Case-insensitive fallback for common mapping issues
        username_lower = username.lower()
        for user, household in USER_HOUSEHOLD.items():
            if user.lower() == username_lower:
                return household
        
        # Special case handling for authentication vs household name mismatches
        if username_lower == 'erez':
            return 'erez_lia'
        elif username_lower == 'lia':
            return 'erez_lia'
        elif username_lower in ['mom', 'dad']:
            return 'parents'
        
        print(f"WARNING: No household found for user '{username}', using 'default'")
        return "default"
        
    except Exception as e:
        print(f"ERROR in get_user_household for '{username}': {e}")
        return "default"


def get_household_users(username):
    """Get all users in the same household as the given user"""
    household = get_user_household(username)
    household_users = HOUSEHOLD_USERS.get(household, [username])
    
    # Handle case where authentication uses different case than household mapping
    if household == 'erez_lia' and username in ['Erez', 'Lia']:
        return ['Erez', 'Lia']  # Return authentication case for consistency
    elif household == 'parents' and username in ['mom', 'dad']:
        return ['mom', 'dad']
    
    return household_users


def get_default_people(username=None):
    """Get default people list for the user's household"""
    if username:
        return get_household_users(username)
    return DEFAULT_PEOPLE


def add_expense(tx_date, category, amount, payer, notes, split_with=None):
    print(f"DEBUG: Adding expense - Date: {tx_date}, Category: {category}, Amount: {amount}, Payer: {payer}, Split: {split_with}")
    conn = get_conn()
    cur = conn.cursor()
    
    # Get household for the payer
    household = get_user_household(payer)
    print(f"DEBUG: Using household '{household}' for user '{payer}'")
    
    if USE_POSTGRES:
        cur.execute(
            "INSERT INTO expenses (ts, tx_date, category, amount, payer, notes, split_with, household) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
            (datetime.utcnow(), tx_date, category, float(amount), payer, notes, split_with, household),
        )
    else:
        cur.execute(
            "INSERT INTO expenses (ts, tx_date, category, amount, payer, notes, split_with, household) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (datetime.utcnow().isoformat(timespec="seconds"), tx_date, category, float(amount), payer, notes, split_with, household),
        )
    
    conn.commit()
    conn.close()
    print(f"DEBUG: Expense added successfully to database with household '{household}'")


def load_expenses(user=None):
    if USE_POSTGRES or Path(DB_PATH).exists():
        conn = get_conn()
        
        if user:
            # Filter by household
            household = get_user_household(user)
            household_users = get_household_users(user)
            household_users_str = "', '".join(household_users)
            
            query = f"""
            SELECT * FROM expenses 
            WHERE household = '{household}' OR payer IN ('{household_users_str}') 
            ORDER BY tx_date DESC, id DESC
            """
            print(f"DEBUG: Loading expenses for user '{user}' in household '{household}' with users: {household_users}")
            print(f"DEBUG: Query = {query}")
        else:
            query = "SELECT * FROM expenses ORDER BY tx_date DESC, id DESC"
            print("DEBUG: Loading all expenses (no user filter)")
        
        df = pd.read_sql_query(query, conn, parse_dates=["tx_date"])
        conn.close()
        print(f"DEBUG: Loaded {len(df)} expenses from database")
        return df
    else:
        print("DEBUG: No database found, returning empty DataFrame")
        return pd.DataFrame()


def delete_row(row_id):
    conn = get_conn()
    cur = conn.cursor()
    
    if USE_POSTGRES:
        cur.execute("DELETE FROM expenses WHERE id = %s", (row_id,))
    else:
        cur.execute("DELETE FROM expenses WHERE id = ?", (row_id,))
    
    conn.commit()
    conn.close()


def get_expense_by_id(expense_id):
    """Get a single expense by ID"""
    conn = get_conn()
    cur = conn.cursor()
    
    if USE_POSTGRES:
        cur.execute("SELECT id, tx_date, category, amount, payer, notes, split_with FROM expenses WHERE id = %s", (expense_id,))
    else:
        cur.execute("SELECT id, tx_date, category, amount, payer, notes, split_with FROM expenses WHERE id = ?", (expense_id,))
    
    result = cur.fetchone()
    conn.close()
    
    if result:
        return {
            'id': result[0],
            'tx_date': result[1],
            'category': result[2], 
            'amount': result[3],
            'payer': result[4],
            'notes': result[5] or '',
            'split_with': result[6] or ''
        }
    return None


def update_expense(expense_id, tx_date, category, amount, payer, notes, split_with=None):
    """Update an existing expense"""
    conn = get_conn()
    cur = conn.cursor()
    
    if USE_POSTGRES:
        cur.execute(
            """UPDATE expenses 
               SET tx_date = %s, category = %s, amount = %s, payer = %s, notes = %s, split_with = %s
               WHERE id = %s""",
            (tx_date, category, float(amount), payer, notes, split_with, expense_id)
        )
    else:
        cur.execute(
            """UPDATE expenses 
               SET tx_date = ?, category = ?, amount = ?, payer = ?, notes = ?, split_with = ?
               WHERE id = ?""",
            (tx_date, category, float(amount), payer, notes, split_with, expense_id)
        )
    
    conn.commit()
    conn.close()


def get_user_budgets(username):
    """Get all budget limits for a specific user from database"""
    # TEMPORARY FIX: Always start with hardcoded budgets as fallback
    fallback_budgets = BUDGET_LIMITS.get(username, {})
    print(f"DEBUG: Hardcoded fallback for {username}: {fallback_budgets}")
    
    try:
        conn = get_conn()
        cur = conn.cursor()
        
        # Check if user_budgets table exists
        if USE_POSTGRES:
            cur.execute("SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'user_budgets')")
            table_exists = cur.fetchone()[0]
        else:
            cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='user_budgets'")
            table_exists = bool(cur.fetchone())
        
        print(f"DEBUG: user_budgets table exists: {table_exists}")
        
        if not table_exists:
            print("DEBUG: user_budgets table missing, using hardcoded fallback")
            conn.close()
            return fallback_budgets
            
        # Get household for the user
        household = get_user_household(username)
        
        if USE_POSTGRES:
            cur.execute("SELECT category, budget_limit FROM user_budgets WHERE username = %s AND household = %s", (username, household))
        else:
            cur.execute("SELECT category, budget_limit FROM user_budgets WHERE username = ? AND household = ?", (username, household))
        
        budgets = {}
        rows = cur.fetchall()
        print(f"DEBUG: Found {len(rows)} budget records for user '{username}' in database")
        
        for row in rows:
            category, budget_limit = row
            budgets[category] = float(budget_limit)
            print(f"DEBUG: DB {username}/{category}: ₪{budget_limit}")
        
        conn.close()
        
        # If no database records found, use hardcoded fallback
        if not budgets:
            print(f"DEBUG: No database records for {username}, using hardcoded fallback")
            return fallback_budgets
        
        # Merge database with fallback (database overrides hardcoded)
        final_budgets = fallback_budgets.copy()
        final_budgets.update(budgets)
        
        print(f"DEBUG: Final merged budget data for {username}: {final_budgets}")
        return final_budgets
        
    except Exception as e:
        print(f"ERROR getting user budgets for {username}: {e}")
        print(f"DEBUG: Using hardcoded fallback due to error")
        return fallback_budgets


def set_user_budget(username, category, budget_limit):
    """Set or update a budget limit for a user and category"""
    print(f"SET_BUDGET DEBUG: Setting budget for user '{username}', category '{category}', amount {budget_limit}")
    
    try:
        conn = get_conn()
        cur = conn.cursor()
        
        # Get household for the user with fallback to 'default'
        try:
            household = get_user_household(username)
            print(f"SET_BUDGET DEBUG: User '{username}' belongs to household '{household}'")
        except Exception as e:
            print(f"SET_BUDGET WARNING: Household lookup failed for '{username}': {e}, using 'default'")
            household = 'default'
        
        # First try to ensure user_budgets table exists (production safety)
        try:
            if USE_POSTGRES:
                cur.execute("SELECT 1 FROM user_budgets LIMIT 1")
            else:
                cur.execute("SELECT 1 FROM user_budgets LIMIT 1")
        except Exception as table_error:
            print(f"SET_BUDGET ERROR: user_budgets table missing or inaccessible: {table_error}")
            # Try to create the table
            try:
                if USE_POSTGRES:
                    cur.execute(
                        """
                        CREATE TABLE IF NOT EXISTS user_budgets (
                            id SERIAL PRIMARY KEY,
                            username TEXT NOT NULL,
                            category TEXT NOT NULL,
                            budget_limit DECIMAL(10,2) NOT NULL,
                            household TEXT DEFAULT 'default',
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            UNIQUE(username, category, household)
                        )
                        """
                    )
                else:
                    cur.execute(
                        """
                        CREATE TABLE IF NOT EXISTS user_budgets (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            username TEXT NOT NULL,
                            category TEXT NOT NULL,
                            budget_limit REAL NOT NULL,
                            household TEXT DEFAULT 'default',
                            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                            UNIQUE(username, category, household)
                        )
                        """
                    )
                conn.commit()
                print(f"SET_BUDGET DEBUG: Created missing user_budgets table")
            except Exception as create_error:
                print(f"SET_BUDGET CRITICAL: Cannot create user_budgets table: {create_error}")
                raise create_error
        
        if USE_POSTGRES:
            cur.execute(
                """
                INSERT INTO user_budgets (username, category, budget_limit, updated_at, household) 
                VALUES (%s, %s, %s, CURRENT_TIMESTAMP, %s)
                ON CONFLICT (username, category, household) 
                DO UPDATE SET budget_limit = EXCLUDED.budget_limit, updated_at = CURRENT_TIMESTAMP
                """,
                (username, category, float(budget_limit), household)
            )
        else:
            cur.execute(
                """
                INSERT OR REPLACE INTO user_budgets (username, category, budget_limit, updated_at, household) 
                VALUES (?, ?, ?, datetime('now'), ?)
                """,
                (username, category, float(budget_limit), household)
            )
        
        conn.commit()
        conn.close()
        print(f"SET_BUDGET DEBUG: Successfully set budget for {username}/{category} = {budget_limit}")
        
    except Exception as e:
        print(f"SET_BUDGET ERROR: Failed to set budget for {username}/{category}: {str(e)}")
        print(f"SET_BUDGET ERROR TYPE: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        raise


def delete_user_budget(username, category):
    """Delete a budget limit for a user and category"""
    print(f"DELETE_BUDGET DEBUG: Deleting budget for user '{username}', category '{category}'")
    
    try:
        conn = get_conn()
        cur = conn.cursor()
        
        # Get household for the user with fallback
        try:
            household = get_user_household(username)
            print(f"DELETE_BUDGET DEBUG: User '{username}' belongs to household '{household}'")
        except Exception as e:
            print(f"DELETE_BUDGET WARNING: Household lookup failed for '{username}': {e}, using 'default'")
            household = 'default'
        
        # Check if table exists first (production safety)
        try:
            if USE_POSTGRES:
                cur.execute("SELECT 1 FROM user_budgets LIMIT 1")
            else:
                cur.execute("SELECT 1 FROM user_budgets LIMIT 1")
        except Exception as table_error:
            print(f"DELETE_BUDGET WARNING: user_budgets table not accessible: {table_error}")
            conn.close()
            return  # Don't fail if table doesn't exist
        
        if USE_POSTGRES:
            cur.execute("DELETE FROM user_budgets WHERE username = %s AND category = %s AND household = %s", (username, category, household))
        else:
            cur.execute("DELETE FROM user_budgets WHERE username = ? AND category = ? AND household = ?", (username, category, household))
        
        rows_affected = cur.rowcount
        conn.commit()
        conn.close()
        print(f"DELETE_BUDGET DEBUG: Successfully deleted {rows_affected} budget record(s) for {username}/{category}")
        
    except Exception as e:
        print(f"DELETE_BUDGET ERROR: Failed to delete budget for {username}/{category}: {str(e)}")
        print(f"DELETE_BUDGET ERROR TYPE: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        # Don't re-raise for delete operations - they're not critical


def cleanup_misc_category():
    """Remove all Misc category entries from user_budgets"""
    try:
        conn = get_conn()
        cur = conn.cursor()
        
        if USE_POSTGRES:
            cur.execute("DELETE FROM user_budgets WHERE category = %s", ("Misc",))
            rows_deleted = cur.rowcount
        else:
            cur.execute("DELETE FROM user_budgets WHERE category = ?", ("Misc",))
            rows_deleted = cur.rowcount
        
        conn.commit()
        conn.close()
        print(f"Cleaned up {rows_deleted} Misc category entries from database")
        return rows_deleted
        
    except Exception as e:
        print(f"Error cleaning up Misc category: {e}")
        return 0


def migrate_budget_limits_to_db():
    """Migrate hardcoded BUDGET_LIMITS to database (run once)"""
    try:
        print("Starting budget migration check...")
        
        # Check each user individually and migrate if they don't have records
        for username, categories in BUDGET_LIMITS.items():
            conn = get_conn()
            cur = conn.cursor()
            
            if USE_POSTGRES:
                cur.execute("SELECT COUNT(*) FROM user_budgets WHERE username = %s", (username,))
            else:
                cur.execute("SELECT COUNT(*) FROM user_budgets WHERE username = ?", (username,))
            
            count = cur.fetchone()[0]
            conn.close()
            
            if count == 0:
                print(f"Migrating budget limits for {username}...")
                for category, limit in categories.items():
                    try:
                        set_user_budget(username, category, limit)
                        print(f"✓ Migrated {username}/{category}: ₪{limit}")
                    except Exception as e:
                        print(f"✗ Error migrating budget for {username}/{category}: {e}")
            else:
                print(f"User {username} already has {count} budget records in database")
            
    except Exception as e:
        print(f"Migration failed: {e}")
        # Try to migrate anyway
        print("Attempting emergency migration...")
        for username, categories in BUDGET_LIMITS.items():
            for category, limit in categories.items():
                try:
                    set_user_budget(username, category, limit)
                except Exception as e:
                    print(f"Error in emergency migration for {username}/{category}: {e}")


app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-for-flash")

# Initialize database on app startup
init_db()
# Run database migrations
migrate_db()
# Migrate hardcoded budget data to database (one-time migration)
migrate_budget_limits_to_db()
# Clean up removed categories
cleanup_misc_category()

# Session cookie hardening (can be disabled for local non-HTTPS testing by setting SESSION_COOKIE_SECURE=0)
secure_cookies = os.environ.get("SESSION_COOKIE_SECURE", "1") != "0"
print(f"CSRF/Session Debug: secure_cookies={secure_cookies}, SECRET_KEY set={'Yes' if app.config['SECRET_KEY'] else 'No'}")
app.config.update(
    SESSION_COOKIE_SECURE=secure_cookies,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
)

# CSRF protection for POST endpoints and forms
csrf = CSRFProtect()
csrf.init_app(app)


def load_users_from_env():
    """Load users from USERS env var: format 'user1:pass1,user2:pass2'. Returns dict username->pw_hash."""
    raw = os.environ.get("USERS")
    users = {}
    if raw:
        for part in raw.split(","):
            if ":" in part:
                u, p = part.split(":", 1)
                users[u.strip()] = generate_password_hash(p.strip())
    else:
        # development fallback (weak default). Encourage setting USERS in production.
        users["Erez"] = generate_password_hash("password")
        users["Lia"] = generate_password_hash("password")
        users["mom"] = generate_password_hash("password")
        users["dad"] = generate_password_hash("password")
        print("Warning: USERS env var not set; using default weak passwords. Set USERS='user:pass,user2:pass,mom:pass,dad:pass' in production.")
    return users


USERS = load_users_from_env()


def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if "user" not in session:
            return redirect(url_for("login", next=request.path))
        return fn(*args, **kwargs)
    return wrapper


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        pw_hash = USERS.get(username)
        if pw_hash and check_password_hash(pw_hash, password):
            session['user'] = username
            next_url = request.args.get('next') or url_for('index')
            return redirect(next_url)
        else:
            flash('Invalid username or password', 'error')
            return redirect(url_for('login'))
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

init_db()


@app.route("/", methods=["GET"])
@login_required
def index():
    # Settings from query params (simple): people and month
    current_user = session.get('user', 'erez')
    household_people = get_default_people(current_user)
    people_raw = request.args.get("people", ", ".join(household_people))
    people = [p.strip() for p in people_raw.split(",") if p.strip()] or household_people

    month_str = request.args.get("month")
    if month_str:
        try:
            month = datetime.fromisoformat(month_str).date()
        except Exception:
            month = date.today().replace(day=1)
    else:
        today = date.today()
        month = date(today.year, today.month, 1)

    month_start = date(month.year, month.month, 1)
    if month.month == 12:
        month_end = date(month.year + 1, 1, 1)
    else:
        month_end = date(month.year, month.month + 1, 1)

    # Load expenses filtered by current user's household
    current_user = session.get('user', 'erez')  # Default to erez for backward compatibility
    df = load_expenses(user=current_user)
    if df.empty:
        dfm = pd.DataFrame()
    else:
        # normalize tx_date to date objects and filter by month
        df["tx_date"] = pd.to_datetime(df["tx_date"]).dt.date
        mask = (pd.to_datetime(df["tx_date"]) >= pd.to_datetime(month_start)) & (pd.to_datetime(df["tx_date"]) < pd.to_datetime(month_end))
        dfm = df[mask].copy()

    total = float(dfm["amount"].sum()) if not dfm.empty else 0.0

    # Prepare safe, JSON/template-friendly structures (native Python types)
    if not dfm.empty:
        by_person_s = dfm.groupby("payer")["amount"].sum().reindex(people, fill_value=0)
        by_person_list = [(str(name), float(by_person_s.get(name, 0.0))) for name in by_person_s.index]

        by_cat_s = dfm.groupby("category")["amount"].sum()
        # sort by amount descending
        by_cat_list = sorted(((str(k), float(v)) for k, v in by_cat_s.items()), key=lambda x: x[1], reverse=True)

        # stringify dates in records so template can render cleanly
        records = []
        for r in dfm.to_dict(orient="records"):
            r2 = dict(r)
            if isinstance(r2.get("tx_date"), (datetime,)):
                r2["tx_date"] = r2["tx_date"].date().isoformat()
            else:
                # if it's already a date object
                try:
                    r2["tx_date"] = r2["tx_date"].isoformat()
                except Exception:
                    r2["tx_date"] = str(r2.get("tx_date"))
            # make sure amounts are native floats
            try:
                r2["amount"] = float(r2.get("amount", 0.0))
            except Exception:
                r2["amount"] = 0.0
            records.append(r2)
    else:
        by_person_list = [(p, 0.0) for p in people]
        by_cat_list = []
        records = []

    import time
    return render_template(
        "index.html",
        people=people,
        categories=CATEGORIES,
        month_start=month_start,
        total=total,
        by_person_list=by_person_list,
        by_cat_list=by_cat_list,
        records=records,
        timestamp=int(time.time()),
    )


@app.route("/add", methods=["POST"])
@login_required
def add():
    try:
        tx_date = request.form.get("tx_date") or date.today().isoformat()
        # Ensure ISO date string (YYYY-MM-DD)
        tx_date_val = datetime.fromisoformat(tx_date).date().isoformat()
    except Exception:
        flash("Invalid date provided", "error")
        return redirect(url_for("index"))

    category = request.form.get("category") or CATEGORIES[0]
    current_user = session.get('user', 'erez')
    household_people = get_default_people(current_user)
    payer = request.form.get("payer") or household_people[0]
    amount = request.form.get("amount") or 0
    notes = request.form.get("notes") or ""
    split_with = request.form.get("split_with") or None

    try:
        if float(amount) <= 0:
            flash("Amount must be positive", "error")
            return redirect(url_for("index"))
    except Exception:
        flash("Invalid amount", "error")
        return redirect(url_for("index"))

    add_expense(tx_date_val, category, amount, payer, notes, split_with)
    flash("Expense added ✅", "success")
    return redirect(url_for("index"))


@app.route("/quick-add", methods=["POST"])
@login_required
def quick_add():
    """Quick add endpoint for predefined expense types"""
    try:
        category = request.form.get("category")
        amount = request.form.get("amount")
        notes = request.form.get("notes", "")
        current_user = session.get('user')
        
        if not category or not amount or not current_user:
            return {"success": False, "message": "Missing required fields"}, 400
        
        # Use today's date for quick adds
        today = date.today().isoformat()
        
        # Validate amount
        try:
            amount_float = float(amount)
            if amount_float <= 0:
                return {"success": False, "message": "Amount must be positive"}, 400
        except (ValueError, TypeError):
            return {"success": False, "message": "Invalid amount"}, 400
        
        # Add the expense
        add_expense(today, category, amount_float, current_user, notes, None)
        
        return {"success": True, "message": f"Added {notes} for ₪{amount_float}"}, 200
        
    except Exception as e:
        print(f"Quick add error: {e}")
        return {"success": False, "message": "Failed to add expense"}, 500


@app.route("/edit/<int:expense_id>", methods=["GET"])
@login_required
def edit_expense_form(expense_id):
    """Show edit form for a specific expense"""
    expense = get_expense_by_id(expense_id)
    if not expense:
        flash("Expense not found", "error")
        return redirect(url_for("index"))
    
    # Convert date to string for HTML date input
    if hasattr(expense['tx_date'], 'isoformat'):
        expense['tx_date'] = expense['tx_date'].isoformat()
    elif isinstance(expense['tx_date'], str):
        # Already a string, ensure it's in ISO format
        try:
            expense['tx_date'] = datetime.fromisoformat(expense['tx_date']).date().isoformat()
        except:
            pass
    
    current_user = session.get('user', 'erez')
    household_people = get_default_people(current_user)
    
    return render_template("edit_expense.html", 
                         expense=expense, 
                         categories=CATEGORIES, 
                         people=household_people)


@app.route("/edit/<int:expense_id>", methods=["POST"])
@login_required
def update_expense_route(expense_id):
    """Update an existing expense"""
    try:
        tx_date = request.form.get("tx_date") or date.today().isoformat()
        # Ensure ISO date string (YYYY-MM-DD)
        tx_date_val = datetime.fromisoformat(tx_date).date().isoformat()
    except Exception:
        flash("Invalid date provided", "error")
        return redirect(url_for("edit_expense_form", expense_id=expense_id))

    category = request.form.get("category") or CATEGORIES[0]
    current_user = session.get('user', 'erez')
    household_people = get_default_people(current_user)
    payer = request.form.get("payer") or household_people[0]
    amount = request.form.get("amount") or 0
    notes = request.form.get("notes") or ""
    split_with = request.form.get("split_with") or None

    try:
        if float(amount) <= 0:
            flash("Amount must be positive", "error")
            return redirect(url_for("edit_expense_form", expense_id=expense_id))
    except Exception:
        flash("Invalid amount", "error")
        return redirect(url_for("edit_expense_form", expense_id=expense_id))

    # Check if expense exists and update it
    existing_expense = get_expense_by_id(expense_id)
    if not existing_expense:
        flash("Expense not found", "error")
        return redirect(url_for("index"))

    update_expense(expense_id, tx_date_val, category, amount, payer, notes, split_with)
    flash("Expense updated successfully ✅", "success")
    return redirect(url_for("index"))


@app.route("/delete", methods=["POST"])
@login_required
def delete():
    row_id = request.form.get("row_id")
    if row_id and row_id.isdigit():
        print(f"DEBUG: Deleting expense row {row_id}")
        delete_row(int(row_id))
        print(f"DEBUG: Row {row_id} deleted from database")
        flash(f"Row {row_id} deleted.", "success")
    else:
        flash("Please enter a numeric ID.", "error")
    return redirect(url_for("index"))


@app.route("/download_csv")
@login_required
def download_csv():
    month = request.args.get("month")
    current_user = session.get('user', 'erez')
    df = load_expenses(user=current_user)
    if df.empty:
        return "No data", 400
    if month:
        try:
            m = datetime.fromisoformat(month).date()
            month_start = date(m.year, m.month, 1)
            if m.month == 12:
                month_end = date(m.year + 1, 1, 1)
            else:
                month_end = date(m.year, m.month + 1, 1)
            df["tx_date"] = pd.to_datetime(df["tx_date"]).dt.date
            mask = (pd.to_datetime(df["tx_date"]) >= pd.to_datetime(month_start)) & (pd.to_datetime(df["tx_date"]) < pd.to_datetime(month_end))
            dfm = df[mask].copy()
        except Exception:
            dfm = df
    else:
        dfm = df

    csv_bytes = dfm.to_csv(index=False).encode("utf-8")
    return send_file(io.BytesIO(csv_bytes), mimetype="text/csv", as_attachment=True, download_name="expenses.csv")


@app.route("/plot/<kind>.png")
@login_required
def plot_png(kind):
    # kind: 'by_cat' or 'by_person' - shows combined data for household users
    current_user = session.get('user', 'erez')
    df = load_expenses(user=current_user)
    if df.empty:
        return "No data", 400
    df["tx_date"] = pd.to_datetime(df["tx_date"]).dt.date
    # default to current month
    today = date.today()
    month_start = date(today.year, today.month, 1)
    if month_start.month == 12:
        month_end = date(month_start.year + 1, 1, 1)
    else:
        month_end = date(month_start.year, month_start.month + 1, 1)

    mask = (pd.to_datetime(df["tx_date"]) >= pd.to_datetime(month_start)) & (pd.to_datetime(df["tx_date"]) < pd.to_datetime(month_end))
    dfm = df[mask].copy()

    if kind == "by_cat":
        by_cat = dfm.groupby("category")["amount"].sum().sort_values(ascending=False)
        fig, ax = plt.subplots(figsize=(8, 6))
        if not by_cat.empty:
            ax.pie(by_cat.values, labels=by_cat.index, autopct="%1.0f%%", startangle=90)
            ax.set_title("Combined Spending by Category", fontsize=14, fontweight='bold')
            ax.axis("equal")
        else:
            ax.text(0.5, 0.5, "No data", ha="center", va="center")
    else:
        by_person = dfm.groupby("payer")["amount"].sum()
        fig, ax = plt.subplots(figsize=(8, 6))
        if not by_person.empty:
            bars = ax.bar(by_person.index, by_person.values, color=['#007bff', '#28a745', '#ffc107', '#dc3545'][:len(by_person)])
            ax.set_ylabel("Amount (₪)")
            ax.set_title("Combined Spending by Person", fontsize=14, fontweight='bold')
            # Add value labels on bars
            for bar in bars:
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height + 5,
                       f'₪{height:.0f}', ha='center', va='bottom')
        else:
            ax.text(0.5, 0.5, "No data", ha="center", va="center")

    plt.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=100, bbox_inches='tight')
    buf.seek(0)
    plt.close(fig)
    response = send_file(buf, mimetype="image/png")
    # Prevent browser caching of chart images
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response


@app.route("/plot/<person>/<kind>.png")
@login_required
def plot_user_png(person, kind):
    # kind: 'by_cat' - shows individual user data within household
    current_user = session.get('user', 'erez')
    df = load_expenses(user=current_user)
    if df.empty:
        return "No data", 400
    df["tx_date"] = pd.to_datetime(df["tx_date"]).dt.date
    # default to current month
    today = date.today()
    month_start = date(today.year, today.month, 1)
    if month_start.month == 12:
        month_end = date(month_start.year + 1, 1, 1)
    else:
        month_end = date(month_start.year, month_start.month + 1, 1)

    # Filter for current month and specific person (case-insensitive)
    mask = (pd.to_datetime(df["tx_date"]) >= pd.to_datetime(month_start)) & \
           (pd.to_datetime(df["tx_date"]) < pd.to_datetime(month_end)) & \
           (df["payer"].str.lower() == person.lower())
    
    dfm = df[mask].copy()

    if kind == "by_cat":
        # Handle split expenses properly
        if not dfm.empty:
            dfm_copy = dfm.copy()
            # For expenses paid by this person that are split, only count half
            split_mask = dfm_copy['split_with'].notna()
            dfm_copy.loc[split_mask, 'amount'] = dfm_copy.loc[split_mask, 'amount'] / 2
            
            # Add expenses where this person was split with (they owe half)
            other_split_mask = (pd.to_datetime(df["tx_date"]) >= pd.to_datetime(month_start)) & \
                             (pd.to_datetime(df["tx_date"]) < pd.to_datetime(month_end)) & \
                             (df["split_with"].str.lower() == person.lower())
            
            other_split_df = df[other_split_mask].copy()
            if not other_split_df.empty:
                other_split_df['amount'] = other_split_df['amount'] / 2
                dfm_copy = pd.concat([dfm_copy, other_split_df], ignore_index=True)
            
            by_cat = dfm_copy.groupby("category")["amount"].sum().sort_values(ascending=False)
        else:
            by_cat = pd.Series([], dtype=float)
        
        fig, ax = plt.subplots(figsize=(8, 6))
        if not by_cat.empty:
            ax.pie(by_cat.values, labels=by_cat.index, autopct="%1.0f%%", startangle=90)
            ax.set_title(f"{person.title()}'s Spending by Category", fontsize=14, fontweight='bold')
            ax.axis("equal")
        else:
            ax.text(0.5, 0.5, f"No data for {person.title()}", ha="center", va="center", fontsize=14)
            ax.set_xlim(0, 1)
            ax.set_ylim(0, 1)
            ax.axis('off')

    plt.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=100, bbox_inches='tight')
    buf.seek(0)
    plt.close(fig)
    response = send_file(buf, mimetype="image/png")
    # Prevent browser caching of chart images
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response


@app.route("/budget/<person>.png")
@login_required
def budget_progress_png(person):
    """Generate budget progress chart for a specific person within household"""
    current_user = session.get('user', 'erez')
    df = load_expenses(user=current_user)
    print(f"DEBUG: Total expenses loaded for household: {len(df)}")
    if df.empty:
        return "No data", 400
    
    # Filter for current month and specific person
    df["tx_date"] = pd.to_datetime(df["tx_date"]).dt.date
    today = date.today()
    month_start = date(today.year, today.month, 1)
    if month_start.month == 12:
        month_end = date(month_start.year + 1, 1, 1)
    else:
        month_end = date(month_start.year, month_start.month + 1, 1)

    print(f"DEBUG: Filtering for {person} from {month_start} to {month_end}")
    mask = (pd.to_datetime(df["tx_date"]) >= pd.to_datetime(month_start)) & \
           (pd.to_datetime(df["tx_date"]) < pd.to_datetime(month_end)) & \
           (df["payer"].str.lower() == person.lower())
    
    person_df = df[mask].copy()
    print(f"DEBUG: Found {len(person_df)} expenses for {person} this month")
    
    # Calculate spending by category (accounting for splits)
    if person_df.empty:
        spent_by_category = pd.Series([], dtype=float)
    else:
        # Calculate actual spending for budget tracking
        person_df_copy = person_df.copy()
        
        # For expenses paid by this person that are split, only count half
        split_mask = person_df_copy['split_with'].notna()
        person_df_copy.loc[split_mask, 'amount'] = person_df_copy.loc[split_mask, 'amount'] / 2
        
        # Add expenses where this person was split with (they owe half)
        if not df.empty:
            # Find expenses where this person was split with
            other_split_mask = (pd.to_datetime(df["tx_date"]) >= pd.to_datetime(month_start)) & \
                             (pd.to_datetime(df["tx_date"]) < pd.to_datetime(month_end)) & \
                             (df["split_with"].str.lower() == person.lower())
            
            other_split_df = df[other_split_mask].copy()
            if not other_split_df.empty:
                # This person owes half of these expenses
                other_split_df['amount'] = other_split_df['amount'] / 2
                # Combine both dataframes
                person_df_copy = pd.concat([person_df_copy, other_split_df], ignore_index=True)
        
        spent_by_category = person_df_copy.groupby("category")["amount"].sum()
    
    # Create budget progress chart
    fig, ax = plt.subplots(figsize=(10, 8))
    
    categories = []
    spent_amounts = []
    remaining_amounts = []
    colors = []
    
    # Get person-specific budget limits from database
    person_budgets = get_user_budgets(person)
    
    for category, budget_limit in person_budgets.items():
        spent = spent_by_category.get(category, 0)
        remaining = max(0, budget_limit - spent)
        
        categories.append(category.replace("Food: ", "").replace("Utilities: ", ""))
        spent_amounts.append(spent)
        remaining_amounts.append(remaining)
        
        # Color coding: red if over budget, yellow if >80%, green if <80%
        if spent > budget_limit:
            colors.append('#ff4444')  # Red - over budget
        elif spent > budget_limit * 0.8:
            colors.append('#ffaa00')  # Orange - warning
        else:
            colors.append('#44aa44')  # Green - safe
    
    # Create horizontal stacked bar chart
    y_pos = range(len(categories))
    
    # Spent amounts (left side)
    bars_spent = ax.barh(y_pos, spent_amounts, color=colors, alpha=0.8, label='Spent')
    
    # Remaining amounts (right side, lighter color)
    bars_remaining = ax.barh(y_pos, remaining_amounts, left=spent_amounts, 
                            color=colors, alpha=0.3, label='Remaining')
    
    # Add budget limit lines
    for i, (category, budget_limit) in enumerate(person_budgets.items()):
        ax.axvline(x=budget_limit, ymin=(i-0.4)/len(categories), ymax=(i+0.4)/len(categories), 
                  color='black', linestyle='--', alpha=0.7, linewidth=2)
    
    ax.set_yticks(y_pos)
    ax.set_yticklabels(categories)
    ax.set_xlabel('Amount (₪)')
    ax.set_title(f'{person} - Budget Progress ({today.strftime("%B %Y")})', fontsize=14, fontweight='bold')
    
    # Add value labels on bars
    for i, (spent, remaining) in enumerate(zip(spent_amounts, remaining_amounts)):
        total_budget = spent + remaining
        if spent > 0:
            ax.text(spent/2, i, f'₪{spent:.0f}', ha='center', va='center', fontweight='bold', color='white')
        if remaining > 0:
            ax.text(spent + remaining/2, i, f'₪{remaining:.0f}', ha='center', va='center', fontweight='bold')
    
    # Add legend
    ax.legend(loc='lower right')
    
    plt.tight_layout()
    
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=100, bbox_inches='tight')
    buf.seek(0)
    plt.close(fig)
    response = send_file(buf, mimetype="image/png")
    # Prevent browser caching of budget chart images
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response


@app.route("/budget/settings")
@login_required  
def budget_settings():
    """Display budget settings page for current user only"""
    current_user = session.get('user')
    if not current_user:
        flash("Please log in to manage your budget", "error")
        return redirect(url_for("login"))
    
    # Only show current user's budget limits from database
    user_budget_limits = get_user_budgets(current_user)
    
    return render_template("budget_settings.html", 
                         budget_limits=user_budget_limits, 
                         categories=CATEGORIES,
                         current_user=current_user)


@app.route("/budget/update", methods=["POST"])
@login_required
def update_budget():
    """Update budget limits for current user only"""
    current_user = session.get('user')
    if not current_user:
        flash("Please log in to manage your budget", "error")
        return redirect(url_for("login"))
    
    print(f"BUDGET UPDATE DEBUG: User '{current_user}' updating budget")
    print(f"BUDGET UPDATE DEBUG: Request form keys: {list(request.form.keys())}")
    print(f"BUDGET UPDATE DEBUG: Session data: {dict(session)}")
    
    # Production compatibility: Check if we have a database connection first
    try:
        conn = get_conn()
        conn.close()
        print("BUDGET UPDATE DEBUG: Database connection successful")
    except Exception as db_error:
        print(f"BUDGET UPDATE ERROR: Database connection failed: {db_error}")
        flash("Database connection error. Please try again.", "error")
        return redirect(url_for("budget_settings"))
    
    success_count = 0
    error_count = 0
    
    try:
        # Update only current user's budget limits in database
        for category in CATEGORIES:
            budget_field = f"budget_{category}"
            budget_value = request.form.get(budget_field)
            print(f"BUDGET UPDATE DEBUG: Processing {budget_field} = '{budget_value}'")
            
            if budget_value and budget_value.strip():
                try:
                    budget_amount = float(budget_value.strip())
                    if budget_amount >= 0:  # Only allow non-negative budgets
                        print(f"BUDGET UPDATE DEBUG: Setting {category} = {budget_amount} for user {current_user}")
                        set_user_budget(current_user, category, budget_amount)
                        success_count += 1
                    else:
                        print(f"BUDGET UPDATE WARNING: Negative budget amount for {category}: {budget_amount}")
                        error_count += 1
                except (ValueError, TypeError) as e:
                    print(f"BUDGET UPDATE ERROR: Invalid budget amount for {category}: {e}")
                    flash(f"Invalid budget amount for {category}: '{budget_value}'", "error")
                    error_count += 1
            else:
                # Remove budget limit if field is empty
                try:
                    print(f"BUDGET UPDATE DEBUG: Removing budget for {category} for user {current_user}")
                    delete_user_budget(current_user, category)
                except Exception as delete_error:
                    print(f"BUDGET UPDATE WARNING: Could not delete budget for {category}: {delete_error}")
                    # Don't count delete errors as failures since the budget might not exist
        
        print(f"BUDGET UPDATE DEBUG: Processed {success_count} successful updates, {error_count} errors")
        
        if success_count > 0:
            flash(f"Budget limits updated successfully! ({success_count} categories)", "success")
        elif error_count == 0:
            flash("Budget settings saved (no changes detected)", "info")
        else:
            flash(f"Some budget updates failed ({error_count} errors)", "warning")
            
        return redirect(url_for("index"))
    
    except Exception as e:
        print(f"BUDGET UPDATE CRITICAL ERROR: {str(e)}")
        print(f"BUDGET UPDATE ERROR TYPE: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        flash(f"Unexpected error updating budget: {str(e)}", "error")
        return redirect(url_for("budget_settings"))


@app.route("/status")
def status():
    """Simple status check - no login required"""
    try:
        conn = get_conn()
        cur = conn.cursor()
        
        if USE_POSTGRES:
            cur.execute("SELECT COUNT(*) FROM expenses")
            count_result = cur.fetchone()
            
            # Get sample expense data to debug date/user issues
            cur.execute("SELECT tx_date, payer, category, amount FROM expenses ORDER BY id DESC LIMIT 3")
            sample_expenses = cur.fetchall()
        else:
            cur.execute("SELECT COUNT(*) FROM expenses")
            count_result = cur.fetchone()
            
            cur.execute("SELECT tx_date, payer, category, amount FROM expenses ORDER BY id DESC LIMIT 3")
            sample_expenses = cur.fetchall()
        
        count = count_result[0] if count_result else 0
        conn.close()
        
        # Current date info for comparison
        today = date.today()
        month_start = date(today.year, today.month, 1)
        
        html = f"""
        <h1>App Status & Debug</h1>
        <p>✅ Database connection: OK</p>
        <p>📊 Total expenses: {count}</p>
        <p>🗄️ Database type: {'PostgreSQL' if USE_POSTGRES else 'SQLite'}</p>
        <p>📅 Current date: {today}</p>
        <p>📅 Current month start: {month_start}</p>
        
        <h3>Sample Expenses (Latest 3):</h3>
        <table border="1">
            <tr><th>Date</th><th>Payer</th><th>Category</th><th>Amount</th></tr>
        """
        
        for expense in sample_expenses:
            html += f"""
            <tr>
                <td>{expense[0]} ({type(expense[0]).__name__})</td>
                <td>"{expense[1]}"</td>
                <td>{expense[2]}</td>
                <td>₪{expense[3]}</td>
            </tr>
            """
        
        html += """
        </table>
        <hr>
        <p><strong>Check if:</strong></p>
        <ul>
            <li>Dates match current month (November 2025)</li>
            <li>Payer names match exactly (case sensitive)</li>
            <li>Date format is correct</li>
        </ul>
        <p><a href="/logs/budget">→ Detailed Budget Logs (login required)</a></p>
        <p><a href="/">→ Main App</a></p>
        """
        
        return html
        
    except Exception as e:
        return f"""
        <h1>App Status</h1>
        <p>❌ Error: {str(e)}</p>
        <p><a href="/">→ Main App</a></p>
        """


@app.route("/cleanup/misc")
def cleanup_misc_route():
    """Manual cleanup route for Misc category - no login required for admin use"""
    try:
        deleted_count = cleanup_misc_category()
        return f"""
        <h1>Misc Category Cleanup</h1>
        <p>✅ Deleted {deleted_count} Misc category entries from database</p>
        <p>The Misc category has been removed from all user budgets.</p>
        <p><a href="/budget/dashboard">→ Check Budget Dashboard</a></p>
        <p><a href="/">→ Main App</a></p>
        """
    except Exception as e:
        return f"""
        <h1>Misc Category Cleanup</h1>
        <p>❌ Error: {str(e)}</p>
        <p><a href="/">→ Main App</a></p>
        """


@app.route("/debug/household")
@login_required
def debug_household():
    """Debug route to show household information for current user"""
    current_user = session.get('user', 'erez')
    household = get_user_household(current_user)
    household_users = get_household_users(current_user)
    
    debug_info = {
        'current_user': current_user,
        'household': household,
        'household_users': household_users,
        'all_household_mappings': HOUSEHOLD_USERS,
        'session_data': dict(session)
    }
    
    return f"<pre>{debug_info}</pre>"


@app.route("/debug/csrf")
def debug_csrf():
    """Debug CSRF and session configuration"""
    try:
        from flask_wtf.csrf import generate_csrf
        csrf_token = generate_csrf()
        session_info = {
            'has_session': 'user' in session,
            'session_user': session.get('user', 'Not logged in'),
            'csrf_token_length': len(csrf_token) if csrf_token else 0,
            'secure_cookies': app.config.get('SESSION_COOKIE_SECURE'),
            'secret_key_set': bool(app.config.get('SECRET_KEY')),
        }
        
        return f"""
        <h1>CSRF & Session Debug</h1>
        <h3>Configuration:</h3>
        <ul>
            <li>Secure Cookies: {session_info['secure_cookies']}</li>
            <li>Secret Key Set: {session_info['secret_key_set']}</li>
            <li>CSRF Token Generated: {csrf_token[:20]}... (length: {session_info['csrf_token_length']})</li>
        </ul>
        <h3>Session:</h3>
        <ul>
            <li>Has Session: {session_info['has_session']}</li>
            <li>Current User: {session_info['session_user']}</li>
        </ul>
        <h3>Fix for Local Development:</h3>
        <p>If getting CSRF errors on localhost, set: <code>export SESSION_COOKIE_SECURE="0"</code></p>
        <p>Or use: <code>./run-local.sh</code> (already configured)</p>
        <p><a href="/">→ Main App</a></p>
        """
    except Exception as e:
        return f"""
        <h1>CSRF Debug Error</h1>
        <p>❌ Error: {str(e)}</p>
        <p><a href="/">→ Main App</a></p>
        """


@app.route("/logs/budget")
@login_required
def logs_budget():
    """Show budget calculation step by step"""
    current_user = session.get('user')
    logs = []
    
    # Step 1: Load expenses
    df = load_expenses()
    logs.append(f"✓ Loaded {len(df)} total expenses from database")
    
    # Step 2: Date filtering setup
    today = date.today()
    month_start = date(today.year, today.month, 1)
    month_end = date(today.year if today.month < 12 else today.year + 1, 
                    today.month + 1 if today.month < 12 else 1, 1)
    logs.append(f"✓ Current user: {current_user}")
    logs.append(f"✓ Date range: {month_start} to {month_end}")
    
    # Step 3: Budget limits
    person_budgets = get_user_budgets(current_user)
    logs.append(f"✓ User budget limits: {len(person_budgets)} categories")
    for cat, amt in person_budgets.items():
        logs.append(f"  - {cat}: ₪{amt}")
    
    # Step 4: Filter expenses
    if not df.empty:
        df["tx_date"] = pd.to_datetime(df["tx_date"]).dt.date
        logs.append(f"✓ Sample dates: {df['tx_date'].head(3).tolist()}")
        logs.append(f"✓ Sample payers: {df['payer'].head(3).tolist()}")
        
        mask = (pd.to_datetime(df["tx_date"]) >= pd.to_datetime(month_start)) & \
               (pd.to_datetime(df["tx_date"]) < pd.to_datetime(month_end)) & \
               (df["payer"] == current_user)
        person_df = df[mask].copy()
        logs.append(f"✓ Filtered expenses: {len(person_df)} for {current_user} this month")
        
        if not person_df.empty:
            logs.append("✓ Your expenses this month:")
            for _, row in person_df.iterrows():
                logs.append(f"  - {row['tx_date']}: ₪{row['amount']} ({row['category']})")
        else:
            logs.append("❌ No expenses found for current user this month!")
    else:
        logs.append("❌ No expenses in database at all!")
    
    # Format as HTML
    html = f"""
    <h1>Budget Calculation Debug Log</h1>
    <p><strong>Time:</strong> {datetime.now()}</p>
    <pre>
"""
    for log in logs:
        html += f"{log}\n"
    
    html += """
    </pre>
    <h3>Quick Actions:</h3>
    <p><a href="/test/add">→ Add Test Expense</a></p>
    <p><a href="/budget/dashboard">→ Budget Dashboard</a></p>
    <p><a href="/">→ Main Dashboard</a></p>
    """
    
    return html


@app.route("/test/add")
@login_required
def test_add():
    """Test adding an expense directly"""
    try:
        current_user = session.get('user')
        today = date.today().isoformat()
        
        # Add a test expense
        add_expense(today, "Food: Groceries", 99.99, current_user, "TEST EXPENSE", None)
        
        # Immediately check if it was saved
        df = load_expenses()
        latest = df.head(1) if not df.empty else None
        
        html = f"""
        <h1>Test Expense Added</h1>
        <p><strong>Added:</strong> ₪99.99 for {current_user} on {today}</p>
        <p><strong>Total expenses now:</strong> {len(df)}</p>
        
        <h3>Latest Expense in Database:</h3>
        """
        
        if latest is not None:
            row = latest.iloc[0]
            html += f"""
            <table border="1">
                <tr><th>ID</th><td>{row['id']}</td></tr>
                <tr><th>Date</th><td>{row['tx_date']}</td></tr>
                <tr><th>Category</th><td>{row['category']}</td></tr>
                <tr><th>Amount</th><td>₪{row['amount']}</td></tr>
                <tr><th>Payer</th><td>{row['payer']}</td></tr>
            </table>
            """
        else:
            html += "<p><strong>ERROR:</strong> No expenses found after adding!</p>"
        
        html += """
        <p><a href="/test/db">→ View All Data</a></p>
        <p><a href="/budget/dashboard">→ Check Budget Dashboard</a></p>
        <p><a href="/">→ Back to Main</a></p>
        """
        
        return html
        
    except Exception as e:
        return f"<h1>Test Error</h1><p>Error: {str(e)}</p><p><a href='/'>← Back</a></p>"


@app.route("/test/db")
@login_required
def test_db():
    """Simple test to verify database operations"""
    try:
        # Test database connection
        conn = get_conn()
        cur = conn.cursor()
        
        # Count total records
        if USE_POSTGRES:
            cur.execute("SELECT COUNT(*) FROM expenses")
        else:
            cur.execute("SELECT COUNT(*) FROM expenses")
        
        total_count = cur.fetchone()[0]
        
        # Get latest 5 records
        if USE_POSTGRES:
            cur.execute("SELECT id, tx_date, category, amount, payer, split_with FROM expenses ORDER BY id DESC LIMIT 5")
        else:
            cur.execute("SELECT id, tx_date, category, amount, payer, split_with FROM expenses ORDER BY id DESC LIMIT 5")
        
        latest_expenses = cur.fetchall()
        conn.close()
        
        # Current user and date info
        current_user = session.get('user')
        today = date.today()
        
        html = f"""
        <h1>Database Test Results</h1>
        <p><strong>Database Type:</strong> {'PostgreSQL' if USE_POSTGRES else 'SQLite'}</p>
        <p><strong>Current User:</strong> {current_user}</p>
        <p><strong>Current Date:</strong> {today}</p>
        <p><strong>Total Expenses in DB:</strong> {total_count}</p>
        
        <h3>Latest 5 Expenses (Raw Database Data):</h3>
        <table border="1" style="border-collapse: collapse;">
            <tr>
                <th>ID</th><th>Date</th><th>Category</th><th>Amount</th><th>Payer</th><th>Split With</th>
            </tr>
        """
        
        for expense in latest_expenses:
            html += f"""
            <tr>
                <td>{expense[0]}</td>
                <td>{expense[1]}</td>
                <td>{expense[2]}</td>
                <td>₪{expense[3]}</td>
                <td>{expense[4]}</td>
                <td>{expense[5] if expense[5] else 'None'}</td>
            </tr>
            """
        
        html += """
        </table>
        
        <h3>Quick Actions:</h3>
        <p><a href="/debug/expenses">→ Full Debug View</a></p>
        <p><a href="/">→ Add New Expense</a></p>
        <p><a href="/budget/dashboard">→ Budget Dashboard</a></p>
        """
        
        return html
        
    except Exception as e:
        return f"<h1>Database Error</h1><p>Error: {str(e)}</p><p><a href='/'>← Back</a></p>"


@app.route("/debug/expenses")
@login_required
def debug_expenses():
    """Debug route to show all expenses and help troubleshoot"""
    df = load_expenses()
    current_user = session.get('user')
    
    if df.empty:
        return f"<h1>No expenses found in database</h1><p>User: {current_user}</p>"
    
    # Convert dates for analysis
    df["tx_date"] = pd.to_datetime(df["tx_date"]).dt.date
    
    # Current month filtering
    today = date.today()
    month_start = date(today.year, today.month, 1)
    month_end = date(today.year if today.month < 12 else today.year + 1, 
                    today.month + 1 if today.month < 12 else 1, 1)
    
    current_month_mask = (pd.to_datetime(df["tx_date"]) >= pd.to_datetime(month_start)) & \
                        (pd.to_datetime(df["tx_date"]) < pd.to_datetime(month_end))
    
    user_expenses = df[df["payer"] == current_user]
    user_current_month = df[current_month_mask & (df["payer"] == current_user)]
    
    html = f"""
    <h1>Expense Debug Info</h1>
    <p><strong>Current User:</strong> {current_user}</p>
    <p><strong>Current Date:</strong> {today}</p>
    <p><strong>Month Range:</strong> {month_start} to {month_end}</p>
    <hr>
    <p><strong>Total Expenses in DB:</strong> {len(df)}</p>
    <p><strong>Your Total Expenses:</strong> {len(user_expenses)}</p>
    <p><strong>Your Current Month Expenses:</strong> {len(user_current_month)}</p>
    <hr>
    <h3>All Expenses:</h3>
    <table border="1">
        <tr><th>ID</th><th>Date</th><th>Category</th><th>Amount</th><th>Payer</th><th>Split</th></tr>
    """
    
    for _, row in df.iterrows():
        html += f"""
        <tr>
            <td>{row['id']}</td>
            <td>{row['tx_date']}</td>
            <td>{row['category']}</td>
            <td>₪{row['amount']}</td>
            <td>{row['payer']}</td>
            <td>{row.get('split_with', 'No')}</td>
        </tr>
        """
    
    html += """
    </table>
    <p><a href="/">← Back to Dashboard</a></p>
    """
    
    return html


@app.route("/budget/dashboard")
@login_required  
def budget_dashboard():
    """Display dedicated budget dashboard page for current user only"""
    current_user = session.get('user')
    if not current_user:
        flash("Please log in to view your budget dashboard", "error")
        return redirect(url_for("login"))
        
    df = load_expenses()
    print(f"BUDGET DEBUG: Loaded {len(df)} total expenses")
    
    # Calculate current month data for budget overview
    today = date.today()
    month_start = date(today.year, today.month, 1)
    if month_start.month == 12:
        month_end = date(month_start.year + 1, 1, 1)
    else:
        month_end = date(month_start.year, month_start.month + 1, 1)
    
    print(f"BUDGET DEBUG: Current user: {current_user}")
    print(f"BUDGET DEBUG: Date range: {month_start} to {month_end}")
    
    # Calculate spending for current user only
    budget_status = {}
    total_spent_by_user = 0
    total_budget_by_user = 0
    
    # Only process current user's data
    budget_status[current_user] = {}
    person_budgets = get_user_budgets(current_user)
    print(f"BUDGET DEBUG: User budgets: {person_budgets}")
        
    # Simplified expense calculation
    spent_by_category = {}
    
    if not df.empty:
        print(f"BUDGET DEBUG: Raw data - first few rows:")
        print(f"BUDGET DEBUG: Dates: {df['tx_date'].head().tolist()}")
        print(f"BUDGET DEBUG: Payers: {df['payer'].head().tolist()}")
        print(f"BUDGET DEBUG: Categories: {df['category'].head().tolist()}")
        
        # Convert dates more reliably
        try:
            df["tx_date_parsed"] = pd.to_datetime(df["tx_date"]).dt.date
        except:
            # If datetime parsing fails, try string parsing
            df["tx_date_parsed"] = df["tx_date"].apply(lambda x: 
                datetime.strptime(str(x)[:10], "%Y-%m-%d").date() if isinstance(x, str) 
                else x if hasattr(x, 'year') 
                else date.today())
        
        print(f"BUDGET DEBUG: Parsed dates: {df['tx_date_parsed'].head().tolist()}")
        
        # Simple filtering - current month and current user (case-insensitive)
        current_month_expenses = df[
            (df['tx_date_parsed'] >= month_start) & 
            (df['tx_date_parsed'] < month_end) & 
            (df['payer'].str.lower() == current_user.lower())
        ].copy()
        
        print(f"BUDGET DEBUG: Found {len(current_month_expenses)} expenses for {current_user} this month")
        
        if not current_month_expenses.empty:
            print(f"BUDGET DEBUG: Current month expenses:")
            for _, expense in current_month_expenses.iterrows():
                print(f"  - {expense['tx_date_parsed']}: ₪{expense['amount']} ({expense['category']})")
            
            # Simple spending calculation (ignore splits for now to debug)
            for _, expense in current_month_expenses.iterrows():
                category = expense['category']
                amount = float(expense['amount'])
                
                if category in spent_by_category:
                    spent_by_category[category] += amount
                else:
                    spent_by_category[category] = amount
        
        print(f"BUDGET DEBUG: Calculated spending by category: {spent_by_category}")
    else:
        print("BUDGET DEBUG: No expenses found in database")
    
    # Calculate budget status for each category for current user
    for category, budget_limit in person_budgets.items():
        spent = spent_by_category.get(category, 0)
        remaining = max(0, budget_limit - spent)
        percentage = (spent / budget_limit * 100) if budget_limit > 0 else 0
        
        print(f"BUDGET DEBUG: {category} - Spent: ₪{spent}, Budget: ₪{budget_limit}")
        
        status = "success"  # Green
        if spent > budget_limit:
            status = "danger"  # Red - over budget
        elif spent > budget_limit * 0.8:
            status = "warning"  # Orange - warning
        
        budget_status[current_user][category] = {
            "spent": spent,
            "budget": budget_limit,
            "remaining": remaining,
            "percentage": percentage,
            "status": status
        }
        
        total_spent_by_user += spent
        total_budget_by_user += budget_limit
    
    print(f"BUDGET DEBUG: Final totals - Spent: ₪{total_spent_by_user}, Budget: ₪{total_budget_by_user}")
    
    import time
    return render_template("budget_dashboard.html", 
                         budget_status=budget_status,
                         total_spent_by_user=total_spent_by_user,
                         total_budget_by_user=total_budget_by_user,
                         current_user=current_user,
                         month_name=today.strftime("%B %Y"),
                         timestamp=int(time.time()))


if __name__ == "__main__":
    # Initialize database
    init_db()
    # Run database migration
    migrate_db()
    # Run migration for split functionality
    migrate_db()
    
    # Bind to 0.0.0.0 so iOS devices on the same network can access the server.
    import os

    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8000"))

    # SSL support: set SSL_CERT and SSL_KEY env vars to point to cert/key files
    ssl_cert = os.environ.get("SSL_CERT") or str(APP_DIR / "cert.pem")
    ssl_key = os.environ.get("SSL_KEY") or str(APP_DIR / "key.pem")

    if Path(ssl_cert).exists() and Path(ssl_key).exists():
        print(f"Starting server with SSL on https://{host}:{port}")
        app.run(host=host, port=port, debug=True, ssl_context=(ssl_cert, ssl_key))
    else:
        print(f"Starting server without SSL on http://{host}:{port}")
        app.run(host=host, port=port, debug=True)
