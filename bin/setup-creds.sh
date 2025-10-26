#!/usr/bin/env bash
set -euo pipefail

# Generates strong credentials for the app and prints export commands.
# Usage:
#   ./bin/setup-creds.sh            # generates creds for 'erez' and 'lia'
#   ./bin/setup-creds.sh alice bob  # generates creds for alice and bob

if ! command -v openssl >/dev/null 2>&1; then
  echo "Error: openssl is required to generate passwords." >&2
  exit 2
fi

USERS=("$@")
if [ ${#USERS[@]} -eq 0 ]; then
  USERS=(erez lia)
fi

pairs=()
echo "Generated credentials:"
for u in "${USERS[@]}"; do
  pass=$(openssl rand -base64 12 | tr -d '\n' | tr -d '=')
  pairs+=("${u}:${pass}")
  printf "  %s : %s\n" "$u" "$pass"
done

# Generate a strong SECRET_KEY using python's secrets module (fallback to openssl if python missing)
if command -v python3 >/dev/null 2>&1; then
  SECRET=$(python3 - <<'PY'
import secrets
print(secrets.token_urlsafe(48))
PY
)
else
  SECRET=$(openssl rand -hex 32)
fi

USERS_STR=$(IFS=,; echo "${pairs[*]}")

cat <<EOF

Copy and paste these into your shell (do NOT commit them):

export USERS='${USERS_STR}'
export SECRET_KEY='${SECRET}'

# For local HTTP development (not recommended for production):
# export SESSION_COOKIE_SECURE=0

# Start the app:
python3 app.py

EOF

exit 0
