#!/usr/bin/env bash
# Create (or reset) a Cognito test user with a permanent password.
#
# Reads USER_POOL_ID / AWS_REGION from .env (populated by deploy_cognito.sh).
#
# Usage:
#   ./scripts/create_test_user.sh                       # interactive prompts
#   ./scripts/create_test_user.sh -u me@example.com     # username (email), hidden password prompt
#   USERNAME=me@example.com PASSWORD='<throwaway-password>' ./scripts/create_test_user.sh  # throwaway automation only
#
# Flags:
#   -u USERNAME   email address used as the Cognito username
#   -p PASSWORD   permanent password; avoid for reusable passwords because shells can log it
#   -f            overwrite an existing user's password (skip create-user error)

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="$ROOT/.env"

# shellcheck disable=SC1091
source "$ROOT/scripts/env.sh"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "✗ .env not found. Run ./scripts/deploy_cognito.sh first." >&2
  exit 1
fi

load_env_file "$ENV_FILE" USER_POOL_ID AWS_REGION

: "${USER_POOL_ID:?USER_POOL_ID missing in .env}"
: "${AWS_REGION:?AWS_REGION missing in .env}"

USERNAME="${USERNAME:-}"
PASSWORD="${PASSWORD:-}"
FORCE=false

while getopts "u:p:f" opt; do
  case "$opt" in
    u) USERNAME="$OPTARG" ;;
    p) PASSWORD="$OPTARG" ;;
    f) FORCE=true ;;
    *) exit 2 ;;
  esac
done

if [[ -z "$USERNAME" ]]; then
  read -rp "Cognito username (email): " USERNAME
fi
if [[ -z "$PASSWORD" ]]; then
  read -rsp "Permanent password (>=8 chars, mixed case + digit): " PASSWORD
  echo
fi

echo "→ admin-create-user $USERNAME (pool=$USER_POOL_ID region=$AWS_REGION)"
if ! aws cognito-idp admin-create-user \
      --user-pool-id "$USER_POOL_ID" \
      --username "$USERNAME" \
      --user-attributes Name=email,Value="$USERNAME" Name=email_verified,Value=true \
      --message-action SUPPRESS \
      --region "$AWS_REGION" >/dev/null 2>&1; then
  if [[ "$FORCE" == true ]]; then
    echo "  user already exists — continuing because -f was given"
  else
    echo "  user already exists. Re-run with -f to reset the password." >&2
    exit 3
  fi
fi

echo "→ admin-set-user-password (permanent)"
PASSWORD_JSON="$(mktemp)"
chmod 600 "$PASSWORD_JSON"
trap 'rm -f "$PASSWORD_JSON"' EXIT
USER_POOL_ID="$USER_POOL_ID" USERNAME="$USERNAME" PASSWORD="$PASSWORD" uv run python - > "$PASSWORD_JSON" <<'PY'
import json
import os
import sys

json.dump(
    {
        "UserPoolId": os.environ["USER_POOL_ID"],
        "Username": os.environ["USERNAME"],
        "Password": os.environ["PASSWORD"],
        "Permanent": True,
    },
    sys.stdout,
)
PY
unset PASSWORD
aws cognito-idp admin-set-user-password \
  --cli-input-json "file://$PASSWORD_JSON" \
  --region "$AWS_REGION" >/dev/null

echo "✔ user ready: $USERNAME"
