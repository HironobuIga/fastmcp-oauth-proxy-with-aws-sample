#!/usr/bin/env bash
# Destroy the sample Cognito CDK stack.

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="$ROOT/.env"

# shellcheck disable=SC1091
source "$ROOT/scripts/env.sh"

if [[ -f "$ENV_FILE" ]]; then
  load_env_file "$ENV_FILE" AWS_REGION
fi

STACK="${STACK:-FastmcpCognitoSampleStack}"
REGION="${CDK_DEFAULT_REGION:-${AWS_REGION:-ap-northeast-1}}"
INFRA_DIR="$ROOT/infrastructure"
FORCE=false

run_cdk() {
  if command -v cdk >/dev/null 2>&1; then
    cdk "$@"
  else
    npx cdk "$@"
  fi
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --stack) STACK="$2"; shift 2 ;;
    --region) REGION="$2"; shift 2 ;;
    --force) FORCE=true; shift ;;
    *) echo "unknown flag: $1" >&2; exit 1 ;;
  esac
done

export CDK_DEFAULT_REGION="$REGION"
: "${CDK_DEFAULT_ACCOUNT:=$(aws sts get-caller-identity --query Account --output text)}"
export CDK_DEFAULT_ACCOUNT

if [[ "$FORCE" != true ]]; then
  printf 'This will destroy stack %s in %s / account %s. Type "destroy" to continue: ' "$STACK" "$REGION" "$CDK_DEFAULT_ACCOUNT"
  read -r CONFIRM
  if [[ "$CONFIRM" != "destroy" ]]; then
    echo "aborted"
    exit 1
  fi
fi

pushd "$INFRA_DIR" >/dev/null
run_cdk destroy "$STACK" --force
popd >/dev/null

echo "destroyed: $STACK"
echo "note: .env is left in place; remove it manually if you no longer need the sample values."
