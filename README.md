# Expense Tracker — Flask

A simple Flask-based shared expense tracker. Add expenses, view charts, export CSV, and use from mobile devices.

## Quick Start

```bash
# Install dependencies
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Set up local credentials (first time only)
cp run-local.sh.example run-local.sh
# Edit run-local.sh with your own usernames and secure passwords

# Generate secure credentials (optional)
./generate-creds.sh

# Run the app
./run-local.sh
```

> **Security**: The `run-local.sh` file is git-ignored to keep your credentials safe. Always use secure passwords!

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

If you prefer to set your own credentials without the script:

```bash
export USERS="your-username:your-secure-password,partner:another-secure-password"
export SECRET_KEY="$(openssl rand -hex 32)"  # Generate secure key
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
