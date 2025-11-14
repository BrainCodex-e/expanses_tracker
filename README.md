# 💸 Advanced Expense Tracker & Budget Management System

A comprehensive full-stack web application for personal expense tracking and budget management. Built with modern web technologies, featuring real-time budget monitoring, expense splitting, and personalized dashboards.

## 🎯 Project Overview

This project demonstrates full-stack development skills including:
- **Backend Architecture**: RESTful Flask API with dual database support
- **Frontend Development**: Responsive Bootstrap UI with interactive charts  
- **Database Design**: Schema evolution and migration handling
- **Security Implementation**: Authentication, authorization, and data protection
- **Cloud Deployment**: Production-ready containerized deployment
- **Data Visualization**: Dynamic chart generation and budget analytics

## 🏗️ Architecture & Technical Stack

### **Backend Technologies**
- **Flask 3.0.0**: Modern Python web framework with blueprints
- **SQLite/PostgreSQL**: Dual database support for dev/production environments
- **Pandas**: Advanced data processing and analytics
- **Matplotlib**: Server-side chart generation
- **Psycopg2**: PostgreSQL adapter with connection pooling
- **Gunicorn**: WSGI HTTP server for production deployment

### **Frontend Technologies**  
- **Bootstrap 5**: Mobile-first responsive framework
- **Vanilla JavaScript**: PWA functionality and service workers
- **Jinja2 Templates**: Server-side rendering with template inheritance
- **CSS3**: Custom styling with CSS variables and flexbox

### **DevOps & Security**
- **Docker**: Containerization for consistent deployments
- **Render**: Cloud platform with automatic CI/CD from GitHub
- **Environment Configuration**: 12-factor app methodology
- **CSRF Protection**: Form security against cross-site attacks
# Expanses Tracker — Full-stack Expense & Budget App

Quick, polished expense tracker built for households. It demonstrates backend engineering (Flask + data modeling), frontend polish (responsive UI, theming), cloud deployment, and realtime collaboration.

Live demo: https://expanses-tracker.onrender.com/  
Roadmap & Supabase migration: SUPABASE_ROADMAP.md

Why this project matters: a compact, real-world example of moving a single-user app to a secure, cloud-native, multi-user system with realtime updates.

---

Core technologies
- Python • Flask 3
- SQLite (local) / PostgreSQL (production) • Supabase (optional)
- Bootstrap 5, Jinja2 templates, vanilla JS
- Pandas + Matplotlib for analytics and charts
- Gunicorn + Render for production hosting

Quick demo (what to show in interviews)
- Login
- Add expense (or quick-add)
- See expense appear in another browser tab (realtime)
- Open budget dashboard and show progress
- Toggle light/dark mode and mobile layout

Get it running (2 commands)
```bash
# 1. create & activate a venv; 2. run the app
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt && python3 app.py
```

Or run locally with the convenience script:
```bash
./run-local.sh
```

Architecture (short)

```
User Browser(s) <---> Flask (Render) <---> Database (SQLite local or Supabase/Postgres)
                       │
                       └─ Realtime Pub/Sub (Supabase) -> Live updates to browsers
```

Key features
- Multi-household support with per-household isolation
- Add / edit / delete expenses, split expenses, notes
- Real-time dashboard updates (Supabase realtime)
- Budget dashboards with progress bars & alerts
- CSV export, PWA-ready, responsive mobile UI
- Deployable on Render; keeps working offline with SQLite

Security & production notes
- Uses hashed passwords, CSRF protection, and secure cookies
- For production, set `DATABASE_URL` (Postgres) and `SECRET_KEY` env vars
- Supabase integration is optional and activated by setting `SUPABASE_URL` and `SUPABASE_ANON_KEY`

Screenshots (placeholders)
- dashboard.png — household overview
- budget.png — per-person budget progress
- mobile.png — mobile layout and quick-add

Interview talking points
- Migration to Supabase: RLS policies, realtime, auth
- UI/UX fixes: dark/light theming, accessibility
- Reliability: keep-alive strategies (GitHub Actions / UptimeRobot)
- Performance trade-offs: server-side charting vs client-side rendering

Extras in this repo
- `supabase_schema.sql` — full DB schema and RLS policies
- `app_supabase_example.py` — example of swapping to Supabase
- `keep_alive.py`, GitHub Action — keep Render app awake on free tier

License
- MIT — feel free to fork and adapt

Contact / Demo
- Live: https://expanses-tracker.onrender.com/  
- Repo: https://github.com/BrainCodex-e/expanses_tracker

---

If you want, I can: (a) add badges (tests/coverage), (b) embed 3 screenshots, or (c) create a short 2-minute demo GIF and update this README with it.
