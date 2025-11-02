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

#+ Expanses Tracker — Flask

This repository contains a small Flask-based shared expense tracker (migrated from Streamlit). It supports adding/deleting expenses, per-person and per-category plots, CSV export, simple session-based authentication, and a PWA shell so you can Add to Home Screen on mobile devices.

## Quick start — local development

```bash
# create & activate a virtualenv (recommended)
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# run the app (development)
python3 app.py
```

By default the dev server listens on port 8000. Open http://127.0.0.1:8000 in your browser.

## Create repo & push (you already did this)
- Repo: https://github.com/BrainCodex-e/expanses_tracker

If you haven't yet pushed, use the `gh` CLI to create a private repo and push:

```bash
git init
git add .
git commit -m "Initial Flask migration: app, templates, PWA, deploy artifacts"
git branch -M main
gh repo create --private --source=. --remote=origin --push
```

## Credentials (local and production)

The app uses an environment variable `USERS` to define allowed usernames and passwords in this format:

USERS='alice:password1,bob:password2'

And a `SECRET_KEY` for Flask sessions. Use the provided helper to generate secure values and copy them into your host's secret store (do not commit these values):

```bash
bash bin/setup-creds.sh
# copy the two export lines it prints and add them to your environment
```

When running locally you can export them in your shell (temporary):

```bash
export USERS="alice:YOURPASS,bob:THEIRPASS"
export SECRET_KEY="a-long-random-secret"
python3 app.py
```

## PWA (Add to Home Screen) and iOS notes

- A minimal `manifest.json` and `sw.js` service worker are included. For a nice home-screen icon replace the placeholder icons in `static/manifest.json` with your own PNGs (192x192 and 512x512).
- iOS requires HTTPS for PWA install. For quick testing without certificates use `ngrok`:

```bash
# start the app
python3 app.py
# in another terminal
ngrok http 8000
```

Open the ngrok HTTPS URL in Safari on your iPhone and use Share → Add to Home Screen.

Limitations: iOS PWAs have reduced service-worker capabilities and limited background execution compared to Android.

ngrok auth and tokens
---------------------

For local usage you typically configure your ngrok authtoken once. This stores a small config in your home directory (not in the repo):

```bash
ngrok config add-authtoken YOUR_NGROK_AUTHTOKEN
```

That writes `~/.ngrok2/ngrok.yml` which includes your authtoken. Do not commit that file. Alternatively you can export a temporary env var for ephemeral runs:

```bash
export NGROK_AUTHTOKEN='...'
ngrok http 8000
```

If you prefer to keep local secrets in the project tree for convenience during development, copy `.env.example` to `.env`, edit the values (USERS, SECRET_KEY, etc.) and then start the app. `.env` is included in `.gitignore`.

## TLS / HTTPS (local testing and production)

- Local testing options:
	- ngrok (recommended for testing on mobile): `ngrok http 8000` (gives a trusted HTTPS URL)
	- Self-signed certs (requires installing/trusting cert on device):

```bash
openssl req -x509 -newkey rsa:4096 -nodes -keyout key.pem -out cert.pem -days 365 -subj "/CN=localhost"
SSL_CERT=cert.pem SSL_KEY=key.pem python3 app.py
```

- Production: use a proper domain + Let's Encrypt. The repo includes a `Dockerfile` and `Procfile` so you can deploy with Gunicorn behind a reverse proxy (nginx) and obtain a real TLS certificate with Certbot.

Cloud Run + Cloud SQL (step-by-step)
-----------------------------------

This project is ready to run on Google Cloud Run. Below are the high-level steps and concrete commands to deploy the container, attach a Cloud SQL Postgres instance, and store sensitive values in Secret Manager.

Prereqs:
- gcloud CLI installed and authenticated
- Billing enabled for your GCP project
- The following APIs enabled: run.googleapis.com, sqladmin.googleapis.com, secretmanager.googleapis.com, artifactregistry.googleapis.com, cloudbuild.googleapis.com

Enable APIs:

```bash
gcloud services enable run.googleapis.com sqladmin.googleapis.com secretmanager.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com
```

Create a Cloud SQL Postgres instance (example):

```bash
gcloud sql instances create expanses-db --database-version=POSTGRES_15 --region=us-central1
gcloud sql databases create expanses --instance=expanses-db
# create a DB user
gcloud sql users create expuser --instance=expanses-db --password="$(openssl rand -base64 16)"
```

Get the connection name (used to attach Cloud SQL to Cloud Run):

```bash
gcloud sql instances describe expanses-db --format='value(connectionName)'
# result is like: project:region:expanses-db
```

Store application secrets in Secret Manager (do NOT put them in code):

```bash
# Create secrets (example values shown; replace with secure generated values)
echo -n "erez:password,lia:password" | gcloud secrets create users-secret --data-file=-
echo -n "$(python3 -c 'import secrets; print(secrets.token_urlsafe(48))')" | gcloud secrets create secret-key --data-file=-
```

Create a service account for CI / GitHub Actions and grant it permissions:

```bash
gcloud iam service-accounts create gha-deployer --display-name="GitHub Actions Deployer"
PROJECT_ID=$(gcloud config get-value project)
gcloud projects add-iam-policy-binding "$PROJECT_ID" --member="serviceAccount:gha-deployer@${PROJECT_ID}.iam.gserviceaccount.com" --role="roles/run.admin"
gcloud projects add-iam-policy-binding "$PROJECT_ID" --member="serviceAccount:gha-deployer@${PROJECT_ID}.iam.gserviceaccount.com" --role="roles/iam.serviceAccountUser"
gcloud projects add-iam-policy-binding "$PROJECT_ID" --member="serviceAccount:gha-deployer@${PROJECT_ID}.iam.gserviceaccount.com" --role="roles/cloudsql.admin"
gcloud projects add-iam-policy-binding "$PROJECT_ID" --member="serviceAccount:gha-deployer@${PROJECT_ID}.iam.gserviceaccount.com" --role="roles/secretmanager.admin"
```

Create and download the service account key, then store it as a GitHub secret named `GCP_SA_KEY` (JSON contents):

```bash
gcloud iam service-accounts keys create key.json --iam-account=gha-deployer@${PROJECT_ID}.iam.gserviceaccount.com
# Copy the contents of key.json into your GitHub repository secret GCP_SA_KEY
```

Create repository secrets (in GitHub) used by the workflow:

- `GCP_PROJECT` — your GCP project id
- `GCP_SA_KEY` — contents of the service account JSON key
- `CLOUD_RUN_REGION` — e.g. us-central1
- `CLOUD_RUN_SERVICE` — e.g. expanses-tracker
- `CLOUD_SQL_CONNECTION_NAME` — the Cloud SQL connection string from above (project:region:instance)
- `SECRET_KEY_SECRET_NAME` — the Secret Manager secret name for SECRET_KEY (e.g. secret-key)
- `USERS_SECRET_NAME` — the Secret Manager secret name for USERS (e.g. users-secret)

Deploy via GitHub Actions
------------------------

I added a GitHub Actions workflow `.github/workflows/deploy-cloud-run.yml` that builds the container using Cloud Build and deploys to Cloud Run. The workflow expects the repository secrets listed above. When you push to `main`, the workflow builds, pushes, and deploys the image.

Automation helpers
------------------

Two helper scripts were added under `bin/` to simplify bootstrapping and running migrations:

- `bin/gcp-bootstrap.sh` — interactive script that enables required APIs, creates a Cloud SQL Postgres instance, creates the database and DB user, stores `USERS` and `SECRET_KEY` into Secret Manager, creates a deploy service account and writes a key file `gha-deployer-key.json`. Run it locally and follow the prompts.

- `bin/run-migrations.sh` — creates and executes a Cloud Run job that runs `alembic upgrade head` against your Cloud SQL instance. Example usage:

```bash
./bin/run-migrations.sh --project=YOUR_PROJECT --region=us-central1 --image=gcr.io/YOUR_PROJECT/expanses-tracker:latest --conn=YOUR_PROJECT:us-central1:expanses-db
```

Note: both scripts call `gcloud` and will create resources in your GCP project. Inspect them before running and ensure you have billing enabled.

Run Alembic migrations
----------------------

Option A — run migrations from your laptop (requires network access to Cloud SQL):

```bash
export DATABASE_URL="postgresql://expuser:THEPASSWORD@//cloudsql/${CLOUD_SQL_CONNECTION_NAME}/expanses"
alembic upgrade head
```

Option B — run migrations as a Cloud Run one-off job (recommended):

```bash
# create a job that runs alembic
gcloud beta run jobs create migrate-job --image gcr.io/${PROJECT_ID}/expanses-tracker:latest --region=${CLOUD_RUN_REGION} --add-cloudsql-instances=${CLOUD_SQL_CONNECTION_NAME} --command "alembic" "upgrade" "head"
gcloud beta run jobs execute migrate-job --region=${CLOUD_RUN_REGION}
```

After migrations run, your service will be backed by Cloud SQL and available at the Cloud Run HTTPS URL.

Notes
-----
- The workflow binds Cloud SQL to the Cloud Run service using the connection name. The app will need `DATABASE_URL` in the format supported by SQLAlchemy for Cloud SQL; the Cloud Run instance will be able to connect to the database over the Cloud SQL socket.
- For production, rotate secrets in Secret Manager and use least-privilege service accounts.


## Deploying to Render (example)

1. Push the repo to GitHub (done).
2. In Render, create a new Web Service and connect your GitHub repo.
3. Use Docker or the build command `pip install -r requirements.txt`. Start command (Procfile works):

```bash
gunicorn -w 4 -b 0.0.0.0:$PORT app:app
```

4. In Render's Dashboard add the following Environment Variables (Secrets):

- `USERS` — value from `bin/setup-creds.sh`
- `SECRET_KEY` — value from `bin/setup-creds.sh`
- `SESSION_COOKIE_SECURE` — `1` (recommended)

5. Deploy. Open the HTTPS URL Render provides and Add to Home Screen on iOS.

Notes: Render's filesystem is ephemeral. If you keep using SQLite (`expenses.db`) you must add backup/export logic or migrate to a managed Postgres database for persistence.

## Runtime & operations

- Start development server: `python3 app.py` (reads `PORT`, `SSL_CERT`, `SSL_KEY` from env if present).
- Production: use Gunicorn (example above). Ensure `SESSION_COOKIE_SECURE=1` in production.

## Security recommendations

- Do not commit `expenses.db`, `.env`, or any PEM keys (a `.gitignore` is included).
- Use strong, unique passwords and rotate `SECRET_KEY` if it may have been exposed.
- Enable rate-limiting on auth (Flask-Limiter) if you expect public traffic.
- For multiple users or scaling, migrate to Postgres and add proper user management (password reset, email verification).

## Developer notes

- Database: currently uses a local SQLite file `expenses.db`. Quick and simple but not suitable for multi-instance production.
- Charts: generated server-side with Matplotlib and served as PNG endpoints.
- CSRF protection via `Flask-WTF` is enabled; forms include CSRF tokens.

## Troubleshooting

- If the app doesn't run on port 8000, set `PORT` env variable before starting: `export PORT=8000`.
- If you accidentally committed secrets, remove them from history and rotate the secret values. Ask me for help with `git filter-repo` or BFG if needed.

## License

This repository contains no external license; add one as you prefer (e.g., MIT) when you're ready to publish.

---

If you'd like, I can:
- Replace the PWA icons with better images in `static/` and update the manifest.
- Add a minimal `docker-compose.yml` for easy local testing with a Postgres service.
- Add simple endpoint tests (pytest + requests) and a GitHub Actions workflow for CI.

Tell me which next step you'd like and I'll do it.
