# Deploying to Render — step by step

This guide walks you through deploying the app to Render.com so it runs 24/7 with HTTPS and environment variables for credentials.

Prerequisites
- A GitHub account and a repo with this project pushed (recommended branch: main).
- A Render account.

Steps

1) Push your repo to GitHub

   ```bash
   git add .
   git commit -m "prepare for render"
   git push origin main
   ```

2) Create a new Web Service on Render

   - In the Render dashboard click "New" → "Web Service".
   - Connect your GitHub repo and choose the `main` branch (or your chosen branch).
   - For Environment choose "Docker" (we included a Dockerfile). If you prefer the native Python environment, choose "Web Service" and set the Start Command to `gunicorn -w 4 -b 0.0.0.0:8000 app:app`.
   - For Docker: Render will build the Dockerfile and run the container.

3) Configure build & start commands (if using native environment)

   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn -w 4 -b 0.0.0.0:8000 app:app`

4) Add environment variables (secrets)

   In the Render service settings, add these environment variables (do NOT commit them to Git):

   - `USERS` — credentials for allowed users in the format `erez:Pass,lia:Pass` (use `bin/setup-creds.sh` to generate).
   - `SECRET_KEY` — random long secret (script above generates one).
   - Optionally: `SESSION_COOKIE_SECURE=1` (default is secure), `PORT=8000`.

5) Enable automatic deploys (optional)

   - In Render, enable automatic deploys so pushing to the branch redeploys the service.

6) Test

   - Once Render builds and deploys, open the HTTPS URL Render provides. Sign in with the usernames you set in `USERS`.
   - Use the browser share menu on iOS to Add to Home Screen (PWA). The site will be served over HTTPS automatically.

Notes & extras
- Database: SQLite (`expenses.db`) will live in the container and is ephemeral — for persistence configure an external Postgres database (Render provides managed databases) and migrate the app to use it. I can scaffold SQLAlchemy + Alembic if you want.
- Backups: If you keep SQLite, implement periodic backups by copying `expenses.db` to object storage or your own backup script.
