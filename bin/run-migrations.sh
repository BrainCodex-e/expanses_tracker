#!/usr/bin/env bash
set -euo pipefail

# Helper to create and execute a Cloud Run job that runs alembic migrations
# Usage:
#   ./bin/run-migrations.sh --project=PROJECT --region=REGION --image=gcr.io/PROJECT/expanses-tracker:TAG --conn=PROJECT:REGION:INSTANCE

usage(){
  cat <<EOF
Usage: $0 --project=PROJECT --region=REGION --image=IMAGE --conn=CLOUD_SQL_CONNECTION_NAME

Example:
  ./bin/run-migrations.sh --project=my-project --region=us-central1 --image=gcr.io/my-project/expanses-tracker:latest --conn=my-project:us-central1:expanses-db
EOF
  exit 1
}

for arg in "$@"; do
  case $arg in
    --project=*) PROJECT="${arg#*=}" ;;
    --region=*) REGION="${arg#*=}" ;;
    --image=*) IMAGE="${arg#*=}" ;;
    --conn=*) CONN="${arg#*=}" ;;
    *) echo "Unknown arg: $arg"; usage ;;
  esac
done

if [ -z "${PROJECT:-}" ] || [ -z "${REGION:-}" ] || [ -z "${IMAGE:-}" ] || [ -z "${CONN:-}" ]; then
  usage
fi

JOB_NAME=migrate-job

echo "Creating Cloud Run job: $JOB_NAME (image: $IMAGE)"
gcloud beta run jobs create "$JOB_NAME" \
  --image "$IMAGE" \
  --region "$REGION" \
  --add-cloudsql-instances="$CONN" \
  --command "alembic" --args "upgrade","head" || true

echo "Executing job $JOB_NAME"
gcloud beta run jobs execute "$JOB_NAME" --region="$REGION"

echo "Migrations job executed. Check job logs in Cloud Console or with 'gcloud beta run jobs executions list'"
