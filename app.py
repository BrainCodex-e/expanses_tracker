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
    "Misc",
    "Arnoni",
]
# Keep these as backend constants for now, but they could be made configurable
DEFAULT_PEOPLE = ["Erez", "Lia"]

# Budget limits per person per category (in ₪)
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
        "Misc": 150,
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
        "Misc": 150,
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
                split_with TEXT DEFAULT NULL
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
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(username, category)
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
                split_with TEXT DEFAULT NULL
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
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(username, category)
            )
            """
        )
        conn.commit()
        conn.close()


def get_conn():
    if USE_POSTGRES:
        return psycopg2.connect(DATABASE_URL)
    else:
        return sqlite3.connect(DB_PATH)


def migrate_db():
    """Add migration for split_with column if it doesn't exist"""
    try:
        conn = get_conn()
        cur = conn.cursor()
        if USE_POSTGRES:
            cur.execute("ALTER TABLE expenses ADD COLUMN IF NOT EXISTS split_with TEXT DEFAULT NULL")
        else:
            # Check if column exists for SQLite
            cur.execute("PRAGMA table_info(expenses)")
            columns = [row[1] for row in cur.fetchall()]
            if 'split_with' not in columns:
                cur.execute("ALTER TABLE expenses ADD COLUMN split_with TEXT DEFAULT NULL")
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Migration warning: {e}")


def add_expense(tx_date, category, amount, payer, notes, split_with=None):
    conn = get_conn()
    cur = conn.cursor()
    
    if USE_POSTGRES:
        cur.execute(
            "INSERT INTO expenses (ts, tx_date, category, amount, payer, notes, split_with) VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (datetime.utcnow(), tx_date, category, float(amount), payer, notes, split_with),
        )
    else:
        cur.execute(
            "INSERT INTO expenses (ts, tx_date, category, amount, payer, notes, split_with) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (datetime.utcnow().isoformat(timespec="seconds"), tx_date, category, float(amount), payer, notes, split_with),
        )
    
    conn.commit()
    conn.close()


def load_expenses():
    if USE_POSTGRES or Path(DB_PATH).exists():
        conn = get_conn()
        df = pd.read_sql_query("SELECT * FROM expenses ORDER BY tx_date DESC, id DESC", conn, parse_dates=["tx_date"])
        conn.close()
        return df
    else:
        return pd.DataFrame()


def delete_row(row_id):
    conn = get_conn()
    cur = conn.cursor()
    
    if USE_POSTGRES:
        cur.execute("DELETE FROM expenses WHERE id = %s", (int(row_id),))
    else:
        cur.execute("DELETE FROM expenses WHERE id = ?", (int(row_id),))
    
    conn.commit()
    conn.close()


def get_user_budgets(username):
    """Get all budget limits for a specific user from database"""
    try:
        conn = get_conn()
        cur = conn.cursor()
        
        if USE_POSTGRES:
            cur.execute("SELECT category, budget_limit FROM user_budgets WHERE username = %s", (username,))
        else:
            cur.execute("SELECT category, budget_limit FROM user_budgets WHERE username = ?", (username,))
        
        budgets = {}
        rows = cur.fetchall()
        print(f"DEBUG: Found {len(rows)} budget records for user '{username}'")
        
        for row in rows:
            category, budget_limit = row
            budgets[category] = float(budget_limit)
            print(f"DEBUG: {username}/{category}: ₪{budget_limit}")
        
        conn.close()
        
        # Always merge with hardcoded defaults to ensure all categories are populated
        final_budgets = {}
        if username in BUDGET_LIMITS:
            final_budgets.update(BUDGET_LIMITS[username])
        final_budgets.update(budgets)  # Database values override hardcoded ones
        
        print(f"DEBUG: Final budget data for {username}: {final_budgets}")
        return final_budgets
        
    except Exception as e:
        print(f"ERROR getting user budgets for {username}: {e}")
        # Fallback to hardcoded limits on error
        return BUDGET_LIMITS.get(username, {})


def set_user_budget(username, category, budget_limit):
    """Set or update a budget limit for a user and category"""
    conn = get_conn()
    cur = conn.cursor()
    
    if USE_POSTGRES:
        cur.execute(
            """
            INSERT INTO user_budgets (username, category, budget_limit, updated_at) 
            VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (username, category) 
            DO UPDATE SET budget_limit = EXCLUDED.budget_limit, updated_at = CURRENT_TIMESTAMP
            """,
            (username, category, float(budget_limit))
        )
    else:
        cur.execute(
            """
            INSERT OR REPLACE INTO user_budgets (username, category, budget_limit, updated_at) 
            VALUES (?, ?, ?, datetime('now'))
            """,
            (username, category, float(budget_limit))
        )
    
    conn.commit()
    conn.close()


def delete_user_budget(username, category):
    """Delete a budget limit for a user and category"""
    conn = get_conn()
    cur = conn.cursor()
    
    if USE_POSTGRES:
        cur.execute("DELETE FROM user_budgets WHERE username = %s AND category = %s", (username, category))
    else:
        cur.execute("DELETE FROM user_budgets WHERE username = ? AND category = ?", (username, category))
    
    conn.commit()
    conn.close()


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

# Session cookie hardening (can be disabled for local non-HTTPS testing by setting SESSION_COOKIE_SECURE=0)
secure_cookies = os.environ.get("SESSION_COOKIE_SECURE", "1") != "0"
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
        print("Warning: USERS env var not set; using default weak passwords. Set USERS='user:pass,user2:pass' in production.")
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
    people_raw = request.args.get("people", ", ".join(DEFAULT_PEOPLE))
    people = [p.strip() for p in people_raw.split(",") if p.strip()] or DEFAULT_PEOPLE

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

    df = load_expenses()
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

    return render_template(
        "index.html",
        people=people,
        categories=CATEGORIES,
        month_start=month_start,
        total=total,
        by_person_list=by_person_list,
        by_cat_list=by_cat_list,
        records=records,
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
    payer = request.form.get("payer") or DEFAULT_PEOPLE[0]
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


@app.route("/delete", methods=["POST"])
@login_required
def delete():
    row_id = request.form.get("row_id")
    if row_id and row_id.isdigit():
        delete_row(int(row_id))
        flash(f"Row {row_id} deleted.", "success")
    else:
        flash("Please enter a numeric ID.", "error")
    return redirect(url_for("index"))


@app.route("/download_csv")
@login_required
def download_csv():
    month = request.args.get("month")
    df = load_expenses()
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
    # kind: 'by_cat' or 'by_person'
    df = load_expenses()
    if df.empty:
        return "No data", 400
    df["tx_date"] = pd.to_datetime(df["tx_date"]).dt.date
    # default to last month
    today = date.today()
    month_start = date(today.year, today.month, 1)
    if month_start.month == 12:
        month_end = date(month_start.year + 1, 1, 1)
    else:
        month_end = date(month_start.year, month_start.month + 1, 1)

    mask = (pd.to_datetime(df["tx_date"]) >= pd.to_datetime(month_start)) & (pd.to_datetime(df["tx_date"]) < pd.to_datetime(month_end))
    dfm = df[mask].copy()
    buf = io.BytesIO()
    plt.tight_layout()

    if kind == "by_cat":
        by_cat = dfm.groupby("category")["amount"].sum().sort_values(ascending=False)
        fig, ax = plt.subplots(figsize=(6, 4))
        if not by_cat.empty:
            ax.pie(by_cat.values, labels=by_cat.index, autopct="%1.0f%%", startangle=90)
            ax.axis("equal")
        else:
            ax.text(0.5, 0.5, "No data", ha="center")
    else:
        by_person = dfm.groupby("payer")["amount"].sum()
        fig, ax = plt.subplots(figsize=(6, 4))
        if not by_person.empty:
            ax.bar(by_person.index, by_person.values)
            ax.set_ylabel("₪")
        else:
            ax.text(0.5, 0.5, "No data", ha="center")

    fig.savefig(buf, format="png")
    buf.seek(0)
    return send_file(buf, mimetype="image/png")


@app.route("/budget/<person>.png")
@login_required
def budget_progress_png(person):
    """Generate budget progress chart for a specific person"""
    df = load_expenses()
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

    mask = (pd.to_datetime(df["tx_date"]) >= pd.to_datetime(month_start)) & \
           (pd.to_datetime(df["tx_date"]) < pd.to_datetime(month_end)) & \
           (df["payer"] == person)
    
    person_df = df[mask].copy()
    
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
                             (df["split_with"] == person)
            
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
    return send_file(buf, mimetype="image/png")


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
    
    # Update only current user's budget limits in database
    for category in CATEGORIES:
        budget_value = request.form.get(f"budget_{category}")
        if budget_value:
            try:
                budget_amount = float(budget_value)
                if budget_amount >= 0:  # Only allow non-negative budgets
                    set_user_budget(current_user, category, budget_amount)
            except (ValueError, TypeError):
                flash(f"Invalid budget amount for {category}", "error")
                return redirect(url_for("budget_settings"))
        else:
            # Remove budget limit if field is empty
            delete_user_budget(current_user, category)
    
    flash("Budget limits updated successfully!", "success")
    return redirect(url_for("index"))


@app.route("/budget/dashboard")
@login_required  
def budget_dashboard():
    """Display dedicated budget dashboard page for current user only"""
    current_user = session.get('user')
    if not current_user:
        flash("Please log in to view your budget dashboard", "error")
        return redirect(url_for("login"))
        
    df = load_expenses()
    
    # Calculate current month data for budget overview
    today = date.today()
    month_start = date(today.year, today.month, 1)
    if month_start.month == 12:
        month_end = date(month_start.year + 1, 1, 1)
    else:
        month_end = date(month_start.year, month_start.month + 1, 1)
    
    # Calculate spending for current user only
    budget_status = {}
    total_spent_by_user = 0
    total_budget_by_user = 0
    
    # Only process current user's data
    budget_status[current_user] = {}
    person_budgets = get_user_budgets(current_user)
        
    if not df.empty:
        # Filter for current month and current user
        df["tx_date"] = pd.to_datetime(df["tx_date"]).dt.date
        mask = (pd.to_datetime(df["tx_date"]) >= pd.to_datetime(month_start)) & \
               (pd.to_datetime(df["tx_date"]) < pd.to_datetime(month_end)) & \
               (df["payer"] == current_user)
        person_df = df[mask].copy()
        
        if not person_df.empty:
            # Calculate actual spending for budget tracking (accounting for splits)
            person_df_copy = person_df.copy()
            
            # For expenses paid by this user that are split, only count half
            split_mask = person_df_copy['split_with'].notna()
            person_df_copy.loc[split_mask, 'amount'] = person_df_copy.loc[split_mask, 'amount'] / 2
            
            # Add expenses where this user was split with (they owe half)
            other_split_mask = (pd.to_datetime(df["tx_date"]) >= pd.to_datetime(month_start)) & \
                             (pd.to_datetime(df["tx_date"]) < pd.to_datetime(month_end)) & \
                             (df["split_with"] == current_user)
            
            other_split_df = df[other_split_mask].copy()
            if not other_split_df.empty:
                # This user owes half of these expenses
                other_split_df['amount'] = other_split_df['amount'] / 2
                # Combine both dataframes
                person_df_copy = pd.concat([person_df_copy, other_split_df], ignore_index=True)
            
            spent_by_category = person_df_copy.groupby("category")["amount"].sum()
        else:
            spent_by_category = pd.Series([], dtype=float)
    else:
        spent_by_category = pd.Series([], dtype=float)
    
    # Calculate budget status for each category for current user
    for category, budget_limit in person_budgets.items():
        spent = spent_by_category.get(category, 0)
        remaining = max(0, budget_limit - spent)
        percentage = (spent / budget_limit * 100) if budget_limit > 0 else 0
        
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
    
    return render_template("budget_dashboard.html", 
                         budget_status=budget_status,
                         total_spent_by_user=total_spent_by_user,
                         total_budget_by_user=total_budget_by_user,
                         current_user=current_user,
                         month_name=today.strftime("%B %Y"))


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
