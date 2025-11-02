#!/usr/bin/env bash
set -euo pipefail

# gcp-bootstrap.sh
# Helper to bootstrap GCP resources for Cloud Run + Cloud SQL deployment.
# Supports interactive prompts (default) and a non-interactive mode for automation.
# Usage (non-interactive):
#   ./bin/gcp-bootstrap.sh --project PROJECT_ID --region REGION --instance INSTANCE_NAME \
#     --db-name DBNAME --db-user DBUSER --cloud-run-service SERVICE_NAME --yes

print_usage() {
  cat <<USAGE
Usage: $0 [options]
Options:
  --project PROJECT_ID           GCP project id (required)
  --region REGION                GCP region (e.g. us-central1)
  --instance INSTANCE_NAME       Cloud SQL instance name
  --db-name DB_NAME              Database name (default: expanses)
  --db-user DB_USER              DB user name (default: expuser)
  --cloud-run-service NAME       Cloud Run service name (default: expanses-tracker)
  --tier TIER                    Cloud SQL instance tier (Postgres requires custom/shared-core). Default: db-custom-1-3840
  -y, --yes, --non-interactive   Assume yes / run without interactive prompts
  -h, --help                     Show this help and exit
Example (non-interactive):
  $0 --project my-proj --region us-central1 --instance expanses-db --yes
USAGE
}

# Defaults
DB_NAME=expanses
DB_USER=expuser
CLOUD_RUN_SERVICE=expanses-tracker
TIER=db-custom-1-3840
ASSUME_YES=0

# Parse args
while [[ $# -gt 0 ]]; do
  case "$1" in
    --project)
      PROJECT="$2"; shift 2;;
    --region)
      REGION="$2"; shift 2;;
    --instance)
      INSTANCE_NAME="$2"; shift 2;;
    --db-name)
      DB_NAME="$2"; shift 2;;
    --db-user)
      DB_USER="$2"; shift 2;;
    --cloud-run-service)
      CLOUD_RUN_SERVICE="$2"; shift 2;;
      --tier)
        TIER="$2"; shift 2;;
    -y|--yes|--non-interactive)
      ASSUME_YES=1; shift;;
    -h|--help)
      print_usage; exit 0;;
    *)
      echo "Unknown argument: $1"; print_usage; exit 1;;
  esac
done

# Check for gcloud
if ! command -v gcloud >/dev/null 2>&1; then
  cat <<MSG
gcloud CLI not found in PATH. Please install and authenticate the Google Cloud SDK before running this script.
Recommended (Linux):
  sudo snap install google-cloud-cli --classic
  gcloud init
Or follow: https://cloud.google.com/sdk/docs/install
MSG
  exit 2
fi

# Interactive prompts for any missing values (unless --yes)
if [[ -z "${PROJECT:-}" ]]; then
  if [[ $ASSUME_YES -eq 0 ]]; then
    read -rp "GCP project id: " PROJECT
  else
    echo "--project is required in non-interactive mode"; exit 1
  fi
fi

if [[ -z "${REGION:-}" ]]; then
  if [[ $ASSUME_YES -eq 0 ]]; then
    read -rp "GCP region (e.g. us-central1): " REGION
  else
    REGION=us-central1
    echo "Using default region: $REGION"
  fi
fi

if [[ -z "${INSTANCE_NAME:-}" ]]; then
  if [[ $ASSUME_YES -eq 0 ]]; then
    read -rp "Cloud SQL instance name (e.g. expanses-db): " INSTANCE_NAME
  else
    echo "--instance is required in non-interactive mode"; exit 1
  fi
fi

# Interactive defaults
if [[ $ASSUME_YES -eq 0 ]]; then
  read -rp "Database name (default: ${DB_NAME}): " DB_NAME_INPUT
  DB_NAME=${DB_NAME_INPUT:-$DB_NAME}
  read -rp "DB user name (default: ${DB_USER}): " DB_USER_INPUT
  DB_USER=${DB_USER_INPUT:-$DB_USER}
  read -rp "Cloud Run service name (default: ${CLOUD_RUN_SERVICE}): " CR_INPUT
  CLOUD_RUN_SERVICE=${CR_INPUT:-$CLOUD_RUN_SERVICE}
fi

echo
echo "This script will enable required APIs and create the following resources in project: $PROJECT"
cat <<EOF
  - Cloud SQL Postgres instance: $INSTANCE_NAME (region: $REGION)
  - Database: $DB_NAME
  - DB user: $DB_USER (password will be randomly generated)
  - Secret Manager secrets: users-secret and secret-key (created or updated)
  - Service account: gha-deployer with deploy permissions and a key file (gha-deployer-key.json)

You will need to add the generated service account key JSON contents to your GitHub repo secrets as GCP_SA_KEY.
EOF

if [[ $ASSUME_YES -eq 0 ]]; then
  read -rp "Continue and create resources? (y/N) " CONF
  if [[ "${CONF,,}" != "y" ]]; then
    echo "Aborting. No changes made."
    exit 0
  fi
else
  echo "Running in non-interactive mode (assume yes)."
fi

echo "Setting gcloud project to $PROJECT"
gcloud config set project "$PROJECT"

echo "Enabling required APIs..."
gcloud services enable run.googleapis.com sqladmin.googleapis.com secretmanager.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com

echo "Creating Cloud SQL instance: $INSTANCE_NAME (tier: $TIER)"
gcloud sql instances create "$INSTANCE_NAME" --database-version=POSTGRES_15 --region="$REGION" --tier="$TIER"

echo "Creating database: $DB_NAME"
gcloud sql databases create "$DB_NAME" --instance="$INSTANCE_NAME"

DB_PASS=$(openssl rand -base64 16)
echo "Creating DB user: $DB_USER"
gcloud sql users create "$DB_USER" --instance="$INSTANCE_NAME" --password="$DB_PASS" || true

CONN_NAME=$(gcloud sql instances describe "$INSTANCE_NAME" --format='value(connectionName)')
echo "Cloud SQL connection name: $CONN_NAME"

echo "Creating Secret Manager secrets (users-secret, secret-key)"
if [[ $ASSUME_YES -eq 0 ]]; then
  read -rp "Enter comma-separated users (example: alice:pass,bob:pass) [default: erez:password,lia:password]: " USERS_VAL
  USERS_VAL=${USERS_VAL:-erez:password,lia:password}
else
  USERS_VAL=${USERS_VAL:-erez:password,lia:password}
  echo "Using default USERS value (override with USERS_VAL env var before running): $USERS_VAL"
fi

# Create or update secret helper
create_or_update_secret() {
  local name="$1" datafile="$2"
  if gcloud secrets describe "$name" >/dev/null 2>&1; then
    gcloud secrets versions add "$name" --data-file="$datafile"
  else
    gcloud secrets create "$name" --data-file="$datafile"
  fi
}

printf "%s" "$USERS_VAL" | create_or_update_secret users-secret /dev/stdin

SECRET_KEY_VAL=$(python3 - <<'PY'
import secrets
print(secrets.token_urlsafe(48))
PY
)
printf "%s" "$SECRET_KEY_VAL" | create_or_update_secret secret-key /dev/stdin

echo "Creating service account: gha-deployer"
gcloud iam service-accounts create gha-deployer --display-name="GitHub Actions Deployer" || true
SA_EMAIL="gha-deployer@${PROJECT}.iam.gserviceaccount.com"

echo "Granting roles to the service account (run.admin, iam.serviceAccountUser, cloudsql.admin, secretmanager.admin)"
gcloud projects add-iam-policy-binding "$PROJECT" --member="serviceAccount:${SA_EMAIL}" --role="roles/run.admin" || true
gcloud projects add-iam-policy-binding "$PROJECT" --member="serviceAccount:${SA_EMAIL}" --role="roles/iam.serviceAccountUser" || true
gcloud projects add-iam-policy-binding "$PROJECT" --member="serviceAccount:${SA_EMAIL}" --role="roles/cloudsql.admin" || true
gcloud projects add-iam-policy-binding "$PROJECT" --member="serviceAccount:${SA_EMAIL}" --role="roles/secretmanager.admin" || true

echo "Creating service account key file: gha-deployer-key.json"
gcloud iam service-accounts keys create gha-deployer-key.json --iam-account="$SA_EMAIL"

cat <<EOF

Bootstrap complete.

Next steps (copy these into your GitHub repository settings):
  - Create GitHub secrets:
      GCP_PROJECT = $PROJECT
      GCP_SA_KEY = (contents of file gha-deployer-key.json)
      CLOUD_RUN_REGION = $REGION
      CLOUD_RUN_SERVICE = $CLOUD_RUN_SERVICE
      CLOUD_SQL_CONNECTION_NAME = $CONN_NAME
      SECRET_KEY_SECRET_NAME = secret-key
      USERS_SECRET_NAME = users-secret

Local info:
  - DB user: $DB_USER
  - DB password: $DB_PASS
  - Cloud SQL connection name: $CONN_NAME
  - Generated SECRET_KEY stored in Secret Manager 'secret-key'.

Remember: do NOT commit gha-deployer-key.json or any secret values to git.

EOF

exit 0
