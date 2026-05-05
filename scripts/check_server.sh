#!/usr/bin/env bash
# Validate discovery metadata for a running sample server.

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="$ROOT/.env"

# shellcheck disable=SC1091
source "$ROOT/scripts/env.sh"

if [[ -f "$ENV_FILE" ]]; then
  load_env_file "$ENV_FILE" PORT_CIMD PORT_DCR PORT_TRADITIONAL
fi

PATTERN="${1:-}"
case "$PATTERN" in
  cimd)
    PORT="${PORT_CIMD:-8001}"
    EXPECT_REGISTRATION=false
    EXPECT_CIMD=true
    ;;
  dcr)
    PORT="${PORT_DCR:-8002}"
    EXPECT_REGISTRATION=true
    EXPECT_CIMD=false
    ;;
  traditional)
    PORT="${PORT_TRADITIONAL:-8003}"
    EXPECT_REGISTRATION=false
    EXPECT_CIMD=false
    ;;
  *)
    echo "usage: $0 {cimd|dcr|traditional}" >&2
    exit 2
    ;;
esac

URL="http://localhost:${PORT}/.well-known/oauth-authorization-server"

uv run python - "$URL" "$EXPECT_REGISTRATION" "$EXPECT_CIMD" <<'PY'
import json
import sys
import urllib.error
import urllib.request

url, expect_registration_raw, expect_cimd_raw = sys.argv[1:4]
expect_registration = expect_registration_raw == "true"
expect_cimd = expect_cimd_raw == "true"

try:
    with urllib.request.urlopen(url, timeout=5) as response:
        metadata = json.load(response)
except urllib.error.URLError as exc:
    raise SystemExit(f"server is not reachable at {url}: {exc}") from exc

registration_present = bool(metadata.get("registration_endpoint"))
cimd_present = metadata.get("client_id_metadata_document_supported") is True

print(json.dumps({
    "issuer": metadata.get("issuer"),
    "registration_endpoint": metadata.get("registration_endpoint"),
    "client_id_metadata_document_supported": metadata.get("client_id_metadata_document_supported"),
}, indent=2))

errors = []
if registration_present != expect_registration:
    errors.append(
        f"registration_endpoint expected {expect_registration}, got {registration_present}"
    )
if cimd_present != expect_cimd:
    errors.append(
        "client_id_metadata_document_supported expected "
        f"{expect_cimd}, got {cimd_present}"
    )

if errors:
    raise SystemExit("; ".join(errors))

print("ok: discovery metadata matches expected pattern")
PY
