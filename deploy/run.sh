#!/usr/bin/env bash
#
# Manual run helper for local testing (no systemd). Builds the frontend if
# needed and starts uvicorn in the foreground.
#
# Usage:
#   ./deploy/run.sh
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

export SIMULATOR_CONFIG="${SIMULATOR_CONFIG:-$PROJECT_ROOT/config.yaml}"
export SIMULATOR_DB="${SIMULATOR_DB:-$PROJECT_ROOT/data/simulator.sqlite}"
mkdir -p "$(dirname "$SIMULATOR_DB")"

if [ ! -f "$SIMULATOR_CONFIG" ]; then
  echo "Config not found at $SIMULATOR_CONFIG"
  echo "Copy config.example.yaml to config.yaml and fill in real values."
  exit 1
fi

# Build the SPA if it hasn't been built yet.
if [ ! -d "$PROJECT_ROOT/frontend/dist" ]; then
  echo "==> Building frontend"
  (cd "$PROJECT_ROOT/frontend" && pnpm install && pnpm run build)
fi

# Ensure the virtualenv exists.
if [ ! -d "$PROJECT_ROOT/backend/.venv" ]; then
  echo "==> Creating virtualenv"
  python3 -m venv "$PROJECT_ROOT/backend/.venv"
  "$PROJECT_ROOT/backend/.venv/bin/pip" install --upgrade pip
  "$PROJECT_ROOT/backend/.venv/bin/pip" install -r "$PROJECT_ROOT/backend/requirements.txt"
fi

echo "==> Starting uvicorn on http://0.0.0.0:8000 (Ctrl+C to stop)"
cd "$PROJECT_ROOT/backend"
exec .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
