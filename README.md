# Expanses_tracker (Flask)

This project runs a small Flask-based shared expense tracker (converted from Streamlit).

Quick start (development):

```bash
# create a virtualenv, install deps
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# run the app
python3 app.py
```

Open the app in a browser on your computer at http://127.0.0.1:8000

Access from iOS devices on the same Wi-Fi:

1. Find your computer's local IP (example: 192.168.1.45).
2. Run the app (the server is bound to 0.0.0.0 port 8000):

```bash
python3 app.py
```

3. From the iPhone/iPad, open Safari and visit: http://<your-computer-ip>:8000 (e.g. http://192.168.1.45:8000)

Notes:

TLS / HTTPS (local testing)
--------------------------------
If you want the connection to be encrypted (HTTPS) for testing from iOS devices, you have a few options:

1) Self-signed certificate (local)

Generate a self-signed cert (valid for testing):

```bash
openssl req -x509 -newkey rsa:4096 -nodes -keyout key.pem -out cert.pem -days 365 -subj "/CN=localhost"
```

Place `cert.pem` and `key.pem` in the project root (same folder as `app.py`). The app will detect them automatically and run with HTTPS.

Start the app (explicitly if you want):

```bash
SSL_CERT=cert.pem SSL_KEY=key.pem python3 app.py
```

Note: iOS will reject self-signed certs unless you install and trust the certificate on the device. For quick testing, consider using an HTTPS tunnel (see next).

2) Use ngrok (recommended for easy secure testing)

Install ngrok and run:

```bash
# start the local app (http)
python3 app.py

# in another terminal, forward with TLS
ngrok http 8000
```

Ngrok gives you a public HTTPS URL you can open on iOS without installing certificates.

Trusting a self-signed certificate on iOS (if you must)
- Copy `cert.pem` to the device (email or host temporarily) and open it. iOS will prompt to install a profile.
- After installing, go to Settings → General → About → Certificate Trust Settings and enable full trust for the certificate.

For production use, prefer a proper domain with Let's Encrypt / reverse proxy.

PWA (Add to Home Screen) and mobile testing
-------------------------------------------
I added a simple web manifest and service worker so you can test the app as a PWA.

Quick test (recommended) — ngrok + PWA:

1. Start the app locally with secure credentials (use `bin/setup-creds.sh`):

```bash
./bin/setup-creds.sh
# paste the export lines it prints
python3 app.py
```

2. In another terminal run:

```bash
ngrok http 8000
```

3. Open the HTTPS ngrok URL in Safari on your iPhone. Use the Share menu → Add to Home Screen to install the PWA.

Notes:
- The manifest currently uses placeholder icons (external). Replace `static/manifest.json` icons with your own PNGs (192x192 and 512x512) for a nicer home-screen icon.
- Full PWA features on iOS are limited, but Add to Home Screen provides an app-like fullscreen experience.

Deploying (Render / Railway / Heroku)
------------------------------------
I included a `Dockerfile` and `Procfile` so you can deploy easily to Render, Railway or Heroku.

High-level steps for Render:

1. Push repo to GitHub.
2. Create a new Web Service on Render, connect your repo.
3. Use build command: `pip install -r requirements.txt` and start command: `gunicorn -w 4 -b 0.0.0.0:8000 app:app` (Procfile also works).
4. Add `USERS` and `SECRET_KEY` in Render's environment settings.

Once deployed, open the HTTPS URL on your phone and Add to Home Screen.


Authentication (restrict to you and your girlfriend)
--------------------------------------------------
This app includes a simple session-based login. Set credentials using the `USERS` environment variable before running the server. Format:

```bash
export USERS='erez:strongpassword,lia:anotherpassword'
export SECRET_KEY='a-long-random-secret'
python3 app.py
```

The app hashes the passwords in memory; do not commit secrets to source control. For production deployments use the host's environment variable management (Railway/Render/Heroku dashboard, or systemd environment files).

Making the app available from anywhere (recommended)
-------------------------------------------------
Options:

- Deploy to a cloud host (recommended): Render, Railway, Fly, DigitalOcean App Platform, or a small VPS (DigitalOcean droplet). Use `gunicorn` and a reverse proxy (nginx) with Let's Encrypt to get free TLS certificates. Example (Gunicorn):

```bash
pip install -r requirements.txt
gunicorn -w 2 -b 0.0.0.0:8000 app:app
```

Then configure nginx as a reverse proxy and use Certbot to obtain a real certificate.

- Quick remote testing with HTTPS: use `ngrok` to forward your local port and get an HTTPS URL usable on iOS without trusting self-signed certs:

```bash
python3 app.py
ngrok http 8000
```

Security notes:
- Always use HTTPS for production. Don't expose the app without TLS.
- Use strong passwords and keep the `SECRET_KEY` secret.
- For multiple users or more advanced auth consider integrating OAuth or a proper user table with hashed passwords and password reset flow.
