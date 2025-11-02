from pathlib import Path
import sqlite3
from datetime import datetime, date
import io
import base64

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
from sqlalchemy import create_engine, text, Column, Integer, String, Float, DateTime, Date
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import date as _date

# Define SQLAlchemy models
Base = declarative_base()

class Expense(Base):
    __tablename__ = 'expenses'
    
    id = Column(Integer, primary_key=True)
    ts = Column(DateTime, nullable=False)
    tx_date = Column(Date, nullable=False)
    category = Column(String(100), nullable=False)
    amount = Column(Float, nullable=False)
    payer = Column(String(100), nullable=False)
    notes = Column(String(500))

# Load local .env for development (optional). Don't store real secrets in the repo.
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    # dotenv is optional; if it's not installed the app will still read real environment variables.
    pass

APP_DIR = Path(__file__).parent
DB_PATH = APP_DIR / "expenses.db"

# Database configuration: use DATABASE_URL if provided, otherwise use SQLite file
DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    # default to a local sqlite file
    DATABASE_URL = f"sqlite:///{DB_PATH.as_posix()}"

# When using sqlite, SQLAlchemy needs check_same_thread=False
connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

# Create engine and session factory
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine)

# Ensure tables exist (will create sqlite file if needed)
Base.metadata.create_all(bind=engine)

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
]

DEFAULT_PEOPLE = ["Erez", "Lia"]


def init_db():
    # Tables are created above via SQLAlchemy, this function kept for compatibility
    Base.metadata.create_all(bind=engine)


def add_expense(tx_date, category, amount, payer, notes):
    session = SessionLocal()
    try:
        # tx_date is an ISO date string (YYYY-MM-DD)
        exp = Expense(
            ts=datetime.utcnow(),
            tx_date=_date.fromisoformat(tx_date),
            category=category,
            amount=float(amount),
            payer=payer,
            notes=notes,
        )
        session.add(exp)
        session.commit()
    finally:
        session.close()


def load_expenses():
    # Use pandas to read SQL directly from the engine
    try:
        df = pd.read_sql_query("SELECT * FROM expenses ORDER BY tx_date DESC, id DESC", con=engine, parse_dates=["tx_date"])
    except Exception:
        df = pd.DataFrame()
    return df


def delete_row(row_id):
    session = SessionLocal()
    try:
        session.execute(text("DELETE FROM expenses WHERE id = :id"), {"id": int(row_id)})
        session.commit()
    finally:
        session.close()


app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-for-flash")

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

    try:
        if float(amount) <= 0:
            flash("Amount must be positive", "error")
            return redirect(url_for("index"))
    except Exception:
        flash("Invalid amount", "error")
        return redirect(url_for("index"))

    add_expense(tx_date_val, category, amount, payer, notes)
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


if __name__ == "__main__":
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
