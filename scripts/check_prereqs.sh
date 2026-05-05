#!/usr/bin/env bash
# Check local prerequisites for the FastMCP Cognito sample.

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="$ROOT/.env"
FAIL=0

# shellcheck disable=SC1091
source "$ROOT/scripts/env.sh"

ok() { printf 'ok: %s\n' "$1"; }
warn() { printf 'warn: %s\n' "$1" >&2; }
fail() { printf 'error: %s\n' "$1" >&2; FAIL=1; }

require_command() {
  if command -v "$1" >/dev/null 2>&1; then
    ok "$1 found"
  else
    fail "$1 is not installed or not on PATH"
  fi
}

require_command uv
require_command aws

if command -v cdk >/dev/null 2>&1 || command -v npx >/dev/null 2>&1; then
  ok "CDK CLI available (cdk or npx)"
else
  fail "AWS CDK CLI is not available; install aws-cdk with npm or use npx"
fi

if command -v gh >/dev/null 2>&1; then
  ok "gh found"
  if gh auth status >/dev/null 2>&1; then
    ok "gh authenticated"
  else
    warn "gh is installed but not authenticated; run gh auth login before prepare_cimd_gist.sh"
  fi
else
  warn "gh is not installed; prepare_cimd_gist.sh requires GitHub CLI"
fi

if uv run python -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 12) else 1)' >/dev/null 2>&1; then
  ok "Python 3.12+ available through uv"
else
  fail "uv could not run Python 3.12+"
fi

if aws sts get-caller-identity >/dev/null 2>&1; then
  ok "AWS credentials are valid"
else
  fail "AWS credentials are not configured; run aws configure or AWS SSO login"
fi

if [[ -f "$ENV_FILE" ]]; then
  load_env_file "$ENV_FILE" PORT_CIMD PORT_DCR PORT_TRADITIONAL
fi

PORTS=("${PORT_CIMD:-8001}" "${PORT_DCR:-8002}" "${PORT_TRADITIONAL:-8003}")
uv run python - "${PORTS[@]}" <<'PY'
import socket
import sys

for raw_port in sys.argv[1:]:
    port = int(raw_port)
    with socket.socket() as sock:
        sock.settimeout(0.2)
        busy = sock.connect_ex(("127.0.0.1", port)) == 0
    if busy:
        print(f"warn: port {port} is already in use", file=sys.stderr)
    else:
        print(f"ok: port {port} is available")
PY

if [[ "$FAIL" -ne 0 ]]; then
  exit 1
fi

printf 'ok: prerequisite check completed\n'
