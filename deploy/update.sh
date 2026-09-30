#!/usr/bin/env bash
#
# Redeploy an updated build to an existing installation and restart the service.
# Preserves config.yaml and the data/ directory (SQLite database).
#
# IMPORTANT: run as your NORMAL user (NOT sudo). The frontend build uses your
# user-level Node (fnm/nvm); sudo is called only for the system steps.
#
# Usage:
#   ./deploy/update.sh
#
# Environment overrides:
#   APP_DIR   Deployment directory (default: /opt/haulage-event-simulator)
#   APP_USER  Service user         (default: haulage)
#
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/haulage-event-simulator}"
APP_USER="${APP_USER:-haulage}"
SERVICE_NAME="haulage-simulator"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

if [ "$(id -u)" -eq 0 ]; then
  echo "ERROR: do not run this script with sudo/root. Run as your normal user."
  exit 1
fi

echo "==> Rebuilding frontend"
pushd "$PROJECT_ROOT/frontend" >/dev/null
pnpm install --frozen-lockfile || pnpm install
pnpm run build
popd >/dev/null

echo "==> Syncing backend and built SPA (config.yaml and data/ preserved)"
sudo rsync -a --delete \
  --exclude '.venv' \
  --exclude '__pycache__' \
  --exclude '.pytest_cache' \
  --exclude '.hypothesis' \
  "$PROJECT_ROOT/backend/" "$APP_DIR/backend/"

sudo rsync -a --delete "$PROJECT_ROOT/frontend/dist/" "$APP_DIR/frontend/dist/"

echo "==> Updating Python dependencies"
sudo "$APP_DIR/backend/.venv/bin/pip" install -r "$APP_DIR/backend/requirements.txt"

sudo chown -R "$APP_USER":"$APP_USER" "$APP_DIR/backend" "$APP_DIR/frontend"

echo "==> Restarting service"
sudo systemctl restart "$SERVICE_NAME"
sudo systemctl status "$SERVICE_NAME" --no-pager || true

echo "==> Done. Follow logs with: journalctl -u $SERVICE_NAME -f"
