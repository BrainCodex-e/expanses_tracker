# Expense Tracker — Flask

A simple Flask-based shared expense tracker. Add expenses, view charts, export CSV, and use from mobile devices.

## Quick Start

```bash
# Install dependencies
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Run with example users
./run-local.sh
```
Open http://127.0.0.1:8000 and login with:
- **alice** / password123  
- **bob** / password456

> **Note**: These are example credentials. In production, use secure passwords and consider adding them to `.gitignore`.

### Access from Phone

The server binds to all interfaces, so you can access it from your phone on the same Wi-Fi:

1. Find your computer's IP: `hostname -I`
2. Open Safari on your phone: `http://YOUR_IP:8000`

## Features

- **Add/delete expenses** with person, category, amount
- **Charts** — spending by person and by category  
- **CSV export** of all data
- **PWA support** — Add to Home Screen on iOS
- **Simple auth** — username/password (configurable)

## Development

### Manual Start

If you prefer to set your own credentials:

```bash
export USERS="alice:mypass,bob:theirpass"
export SECRET_KEY="your-secret-key-here" 
export PORT=8000
python3 app.py
```

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

## Cloud Deployment

This project works perfectly on Render's free tier. Just connect your GitHub repo and it auto-deploys with HTTPS!
