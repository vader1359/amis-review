#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
test -f .env || { echo 'Create .env from .env.example first.' >&2; exit 1; }
source .venv/bin/activate
exec uvicorn web.server:app --host "${APP_HOST:-0.0.0.0}" --port "${APP_PORT:-8787}"
