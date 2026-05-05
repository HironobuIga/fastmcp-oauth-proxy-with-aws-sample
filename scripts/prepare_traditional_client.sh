#!/usr/bin/env bash
# Generate and persist the static MCP client used by the traditional pattern.

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="$ROOT/.env"

if [[ ! -f "$ENV_FILE" ]]; then
  cp "$ROOT/.env.example" "$ENV_FILE"
fi

get_env() {
  local key="$1"
  grep -E "^${key}=" "$ENV_FILE" | tail -n 1 | cut -d= -f2- || true
}

upsert() {
  local key="$1"
  local val="$2"
  local esc
  esc=$(printf '%s' "$val" | sed -e 's/[\/&]/\\&/g')
  if grep -q "^$key=" "$ENV_FILE"; then
    sed -i.bak "s/^$key=.*/$key=$esc/" "$ENV_FILE" && rm -f "$ENV_FILE.bak"
  else
    printf '%s=%s\n' "$key" "$val" >> "$ENV_FILE"
  fi
}

mask_secret() {
  local val="$1"
  local len="${#val}"
  if (( len <= 8 )); then
    printf '<hidden>'
  else
    printf '%s...%s' "${val:0:4}" "${val: -4}"
  fi
}

CLIENT_ID="$(get_env TRADITIONAL_MCP_CLIENT_ID)"
CLIENT_SECRET="$(get_env TRADITIONAL_MCP_CLIENT_SECRET)"

if [[ -z "$CLIENT_ID" ]]; then
  CLIENT_ID="fastmcp-sample-traditional"
fi

if [[ -z "$CLIENT_SECRET" ]]; then
  CLIENT_SECRET="$(uv run python -c 'import secrets; print(secrets.token_urlsafe(32))')"
fi

upsert TRADITIONAL_MCP_CLIENT_ID "$CLIENT_ID"
upsert TRADITIONAL_MCP_CLIENT_SECRET "$CLIENT_SECRET"

printf 'TRADITIONAL_MCP_CLIENT_ID=%s\n' "$CLIENT_ID"
printf 'TRADITIONAL_MCP_CLIENT_SECRET=%s (written to .env)\n' "$(mask_secret "$CLIENT_SECRET")"
printf 'updated: %s\n' "$ENV_FILE"
