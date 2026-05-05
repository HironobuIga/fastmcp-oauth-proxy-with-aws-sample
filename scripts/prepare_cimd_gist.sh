#!/usr/bin/env bash
# Create a public GitHub Gist for CIMD metadata and save CIMD_DOC_URL into .env.

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="$ROOT/.env"
TEMPLATE="$ROOT/client/client_metadata.example.json"
FILENAME="client_metadata.example.json"
DESCRIPTION="${CIMD_GIST_DESCRIPTION:-fastmcp cognito cimd demo}"

if ! command -v gh >/dev/null 2>&1; then
  echo "gh is required. Install GitHub CLI and run gh auth login." >&2
  exit 1
fi

if ! gh auth status >/dev/null 2>&1; then
  echo "gh is not authenticated. Run gh auth login first." >&2
  exit 1
fi

if [[ ! -f "$ENV_FILE" ]]; then
  cp "$ROOT/.env.example" "$ENV_FILE"
fi

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

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

INITIAL="$TMP_DIR/$FILENAME"
RENDERED="$TMP_DIR/rendered-$FILENAME"
PATCH_JSON="$TMP_DIR/gist-patch.json"
cp "$TEMPLATE" "$INITIAL"

echo "creating public Gist..."
GIST_URL="$(gh gist create "$INITIAL" --public -d "$DESCRIPTION")"
GIST_ID="${GIST_URL##*/}"
OWNER="$(gh api user --jq .login)"
CIMD_DOC_URL="https://gist.githubusercontent.com/${OWNER}/${GIST_ID}/raw/${FILENAME}"

uv run python "$ROOT/scripts/render_cimd_metadata.py" "$CIMD_DOC_URL" > "$RENDERED"

uv run python - "$FILENAME" "$RENDERED" > "$PATCH_JSON" <<'PY'
import json
import sys
from pathlib import Path

filename = sys.argv[1]
content = Path(sys.argv[2]).read_text(encoding="utf-8")
json.dump({"files": {filename: {"content": content}}}, sys.stdout)
PY

gh api --method PATCH "gists/$GIST_ID" --input "$PATCH_JSON" >/dev/null

echo "waiting for raw Gist URL to serve the patched CIMD document..."
uv run python - "$CIMD_DOC_URL" <<'PY'
import json
import sys
import time
import urllib.error
import urllib.request

url = sys.argv[1]
deadline = time.monotonic() + 180
last_error = "not fetched yet"

while time.monotonic() < deadline:
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            metadata = json.load(response)
        if metadata.get("client_id") == url:
            raise SystemExit(0)
        last_error = f"client_id={metadata.get('client_id')!r}"
    except (AttributeError, OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
        last_error = str(exc)
    time.sleep(3)

raise SystemExit(
    "raw Gist URL did not serve the patched CIMD document within 180 seconds "
    f"({last_error})"
)
PY

upsert CIMD_DOC_URL "$CIMD_DOC_URL"

printf 'CIMD_DOC_URL=%s\n' "$CIMD_DOC_URL"
printf 'updated: %s\n' "$ENV_FILE"
