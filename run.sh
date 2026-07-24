#!/usr/bin/env bash
# Linux/Mac entrypoint for the Streamlit app.
# On Databricks, use `databricks apps deploy` with app.yaml instead.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Load .env if present (dev convenience; production uses injected env vars)
if [ -f "$SCRIPT_DIR/.env" ]; then
  set -a
  # shellcheck disable=SC1091
  source "$SCRIPT_DIR/.env"
  set +a
fi

PORT="${PORT:-8501}"

exec streamlit run "$SCRIPT_DIR/app.py" \
  --server.port "$PORT" \
  --server.address 0.0.0.0 \
  --server.headless true
