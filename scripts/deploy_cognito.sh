#!/usr/bin/env bash
# Deploy the Cognito CDK stack and write outputs into the project .env file.
#
# Requirements:
#   * aws CLI with credentials for the target account
#   * cdk CLI (`npm i -g aws-cdk` or `npx cdk`)
#   * uv
#
# Usage: ./scripts/deploy_cognito.sh [--stack NAME] [--region REGION]

set -euo pipefail

STACK="${STACK:-FastmcpCognitoSampleStack}"
REGION="${CDK_DEFAULT_REGION:-${AWS_REGION:-ap-northeast-1}}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
INFRA_DIR="$ROOT/infrastructure"
ENV_FILE="$ROOT/.env"

run_cdk() {
  if command -v cdk >/dev/null 2>&1; then
    cdk "$@"
  else
    npx cdk "$@"
  fi
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --stack)   STACK="$2"; shift 2 ;;
    --region)  REGION="$2"; shift 2 ;;
    *) echo "unknown flag: $1" >&2; exit 1 ;;
  esac
done

export CDK_DEFAULT_REGION="$REGION"
: "${CDK_DEFAULT_ACCOUNT:=$(aws sts get-caller-identity --query Account --output text)}"
export CDK_DEFAULT_ACCOUNT

echo "→ cdk deploy $STACK (region=$REGION account=$CDK_DEFAULT_ACCOUNT)"
pushd "$INFRA_DIR" >/dev/null
run_cdk deploy "$STACK" --require-approval never
popd >/dev/null

echo "→ reading stack outputs"
OUTPUTS=$(aws cloudformation describe-stacks \
  --stack-name "$STACK" --region "$REGION" \
  --query 'Stacks[0].Outputs' --output json)

get() { echo "$OUTPUTS" | uv run python -c "import json,sys;o=json.load(sys.stdin);print(next((x['OutputValue'] for x in o if x['OutputKey']==sys.argv[1]),''))" "$1"; }

USER_POOL_ID="$(get UserPoolId)"
CLIENT_ID="$(get ClientId)"
HOSTED_UI_DOMAIN="$(get HostedUiDomain)"

echo "→ describe-user-pool-client (to fetch client secret)"
CLIENT_SECRET=$(aws cognito-idp describe-user-pool-client \
  --user-pool-id "$USER_POOL_ID" --client-id "$CLIENT_ID" \
  --region "$REGION" \
  --query 'UserPoolClient.ClientSecret' --output text)

if [[ ! -f "$ENV_FILE" ]]; then cp "$ROOT/.env.example" "$ENV_FILE"; fi

upsert() { local key="$1"; local val="$2"; local esc
  esc=$(printf '%s' "$val" | sed -e 's/[\/&]/\\&/g')
  if grep -q "^$key=" "$ENV_FILE"; then
    sed -i.bak "s/^$key=.*/$key=$esc/" "$ENV_FILE" && rm -f "$ENV_FILE.bak"
  else
    printf '%s=%s\n' "$key" "$val" >> "$ENV_FILE"
  fi
}

upsert AWS_REGION "$REGION"
upsert USER_POOL_ID "$USER_POOL_ID"
upsert COGNITO_CLIENT_ID "$CLIENT_ID"
upsert COGNITO_CLIENT_SECRET "$CLIENT_SECRET"

echo "✔ .env updated. Sign-in domain: https://${HOSTED_UI_DOMAIN}.auth.${REGION}.amazoncognito.com"
