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
- **Password Hashing**: Werkzeug security for credential protection

### Multi-Household Data Isolation

Perfect for families who want separate expense tracking! The system supports multiple households with complete data isolation:

**Household Structure:**
- **Primary Household**: `erez` and `lia` share expenses and budgets
- **Parents Household**: `mom` and `dad` have their own isolated dashboard
- **Data Separation**: Each household only sees their own expenses, charts, and budgets

**User Authentication:**
```bash
# Set up multiple households in environment variables
export USERS="erez:secure_pass1,lia:secure_pass2,mom:parent_pass1,dad:parent_pass2"
```

### Access from Phone

The server binds to all interfaces, so you can access it from your phone on the same Wi-Fi:

1. Find your computer's IP: `hostname -I`
2. Open Safari on your phone: `http://YOUR_IP:8000`
3. Each family member logs in with their own credentials
4. Each household sees only their own financial data

## Features

- **Multi-Household Support** — Complete data isolation between family groups
- **Add/delete expenses** with person, category, amount
- **Expense Splitting** — Split expenses 50/50 between household members
- **Charts** — Individual and combined spending analytics per household
- **Budget Dashboard** — Real-time budget tracking with visual indicators
- **Mobile Gestures** — Touch-friendly swipe-to-delete and quick-add buttons
- **CSV export** of all data
- **PWA support** — Add to Home Screen on iOS
- **Secure Authentication** — Multi-user household access with data isolation

## Development

### Manual Start

If you prefer to set your own credentials without the script:

```bash
# Single household
export USERS="your-username:your-secure-password,partner:another-secure-password"

# Multi-household (parents + children)  
export USERS="erez:pass1,lia:pass2,mom:pass3,dad:pass4"

export SECRET_KEY="$(openssl rand -hex 32)"  # Generate secure key
export PORT=8000
python3 app.py
```

### Recent Updates (November 2025)

🆕 **Multi-Household Isolation System**
- Complete data separation between family groups
- Household-aware charts, budgets, and expense tracking
- Database schema evolution with automatic migration
- Mobile-optimized UI with touch gestures

🆕 **Enhanced Mobile Experience**
- Swipe-to-delete expense cards with haptic feedback
- Quick-add buttons for common expense categories
- Responsive design with CSS animations
- Individual user charts within household context

### Database

Uses SQLite (`expenses.db`) for simplicity. The database is created automatically on first run.

## PWA (Add to Home Screen)

The app includes PWA support. For HTTPS testing (required for iOS PWA install):

### Option 1: ngrok (easiest)
```bash
./run-local.sh
# In another terminal:
ngrok http 8000
```
Open the ngrok HTTPS URL in Safari and use Share → Add to Home Screen.

### Option 2: Self-signed certificate
```bash
openssl req -x509 -newkey rsa:4096 -nodes -keyout key.pem -out cert.pem -days 365 -subj "/CN=localhost"
SSL_CERT=cert.pem SSL_KEY=key.pem ./run-local.sh
```

### Configure ngrok (one-time)
```bash
ngrok config add-authtoken YOUR_NGROK_AUTHTOKEN
```

## Technical Notes

- **Database**: SQLite (`expenses.db`) — created automatically
- **Charts**: Server-side Matplotlib → PNG endpoints  
- **Security**: CSRF protection, session cookies
- **PWA**: Manifest + service worker for Add to Home Screen

## Troubleshooting

**Port conflicts**: Change the port in `run-local.sh` or export `PORT=9000`

**Dependencies**: Make sure you're in the virtualenv: `source .venv/bin/activate`

**Permissions**: The app creates `expenses.db` in the current directory

---

## Fork This Repository

Want to use this expense tracker for your own purposes? Here's how:

1. **Fork this repository** on GitHub
2. **Clone your fork**: `git clone https://github.com/YOUR-USERNAME/expanses_tracker.git`
3. **Set up local credentials**: 
   ```bash
   cp run-local.sh.example run-local.sh
   # Edit run-local.sh with your usernames and secure passwords
   ```
4. **Deploy to Render** (or your preferred platform):
   - Connect your GitHub fork to Render
   - Set environment variables: `USERS` and `SECRET_KEY`
   - Use `./generate-creds.sh` to generate secure values

## Cloud Deployment

### Render (Recommended)
1. Connect your GitHub repository to [Render](https://render.com)
2. Create a Web Service
3. Set environment variables:
   - `USERS`: `username1:password1,username2:password2`
   - `SECRET_KEY`: Use output from `./generate-creds.sh`
4. Deploy! Your app gets HTTPS automatically.

### Other Platforms
This Flask app works on any platform that supports Python web apps (Heroku, Railway, PythonAnywhere, etc.)
