#!/usr/bin/env bash
# Start one of the three FastMCP sample servers.
#   ./scripts/run.sh cimd
#   ./scripts/run.sh dcr
#   ./scripts/run.sh traditional
set -euo pipefail

case "${1:-}" in
  cimd)         exec uv run python -m src.server_cimd ;;
  dcr)          exec uv run python -m src.server_dcr ;;
  traditional)  exec uv run python -m src.server_traditional ;;
  *)            echo "usage: $0 {cimd|dcr|traditional}" >&2; exit 1 ;;
esac
