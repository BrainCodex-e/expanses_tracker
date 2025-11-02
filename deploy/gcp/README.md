Cloud Run + Cloud SQL (Postgres) deployment guide

This guide shows the high-level steps to deploy the app to Google Cloud Run with a managed Cloud SQL (Postgres) instance.

Prerequisites
- gcloud CLI installed and authenticated
- A Google Cloud project with billing enabled
- The Cloud SQL Admin API enabled

High-level steps
1. Create a Cloud SQL (Postgres) instance

```bash
gcloud sql instances create expanses-sql --database-version=POSTGRES_15 --cpu=1 --memory=384Mi --region=us-central1
gcloud sql databases create expanses_db --instance=expanses-sql
```

2. Create a database user and password (store this in secret manager or your CI secrets)

```bash
gcloud sql users set-password postgres --instance=expanses-sql --password="SOME_STRONG_PASSWORD"
```

3. Give Cloud Run service access to Cloud SQL (use a service account) and note the instance connection name:

```bash
gcloud sql instances describe expanses-sql --format="value(connectionName)"
# example: project:us-central1:expanses-sql
```

4. Build and push container (or let Cloud Build do it via `gcloud run deploy`)

5. Deploy to Cloud Run (replace INSTANCE_CONNECTION_NAME and DB credentials)

```bash
gcloud run deploy expanses-tracker \
  --image gcr.io/PROJECT_ID/expanses-tracker:latest \
  --add-cloudsql-instances INSTANCE_CONNECTION_NAME \
  --update-env-vars DATABASE_URL=postgresql+psycopg2://postgres:YOURPASSWORD@/expanses_db?host=/cloudsql/INSTANCE_CONNECTION_NAME,USERS="alice:pass,bob:pass",SECRET_KEY="your-secret-key" \
  --region us-central1 --platform managed
```

Notes:
- We pass a SQLAlchemy-style `DATABASE_URL` that uses the Cloud SQL unix socket path (`host=/cloudsql/INSTANCE_CONNECTION_NAME`). Cloud Run automatically mounts the socket when `--add-cloudsql-instances` is used.
- Instead of putting credentials directly on the command line, store secrets in Secret Manager or the Cloud Run environment variables in the Console.

CI / GitHub Actions
- You can use a GitHub Actions workflow to build and push the image to GCR and then run `gcloud run deploy`. The repo includes a sample workflow in `.github/workflows/deploy-cloud-run.yml`.

If you'd like, I can:
- Create a small GitHub Actions workflow that builds and deploys on push to `main`.
- Add a small `README` snippet to show how to migrate data from SQLite to Postgres using `psql`.
