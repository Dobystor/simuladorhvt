#!/usr/bin/env bash
#
# Installer for the Haulage Event Simulator on a Linux server.
#
# IMPORTANT: run this as your NORMAL user (NOT with sudo), so the frontend build
# uses your user-level Node (e.g. from fnm/nvm). The script calls sudo only for
# the steps that touch the system (copying to /opt, creating the service user,
# installing the systemd unit). You will be prompted for your sudo password.
#
# Usage:
#   ./deploy/install.sh
#
# Environment overrides:
#   APP_DIR   Deployment directory (default: /opt/haulage-event-simulator)
#   APP_USER  Service user         (default: haulage)
#
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/haulage-event-simulator}"
APP_USER="${APP_USER:-haulage}"
SERVICE_NAME="haulage-simulator"

# Directory this script lives in (project root is one level up).
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "==> Project root: $PROJECT_ROOT"
echo "==> Deploy target: $APP_DIR (user: $APP_USER)"

# Refuse to run as root: the build needs the invoking user's Node (fnm/nvm),
# which root cannot see.
if [ "$(id -u)" -eq 0 ]; then
  echo "ERROR: do not run this script with sudo/root."
  echo "Run it as your normal user; it will call sudo only where needed."
  exit 1
fi

# --- 1. Prerequisites check ---------------------------------------------------
command -v python3 >/dev/null || { echo "python3 is required"; exit 1; }
command -v node >/dev/null    || { echo "node is required (v18+)"; exit 1; }

# Vite 6 and pnpm require Node 18 or newer. Fail early with a clear message.
NODE_MAJOR="$(node -p 'process.versions.node.split(".")[0]')"
if [ "$NODE_MAJOR" -lt 18 ]; then
  echo "ERROR: Node.js v18+ is required, but found $(node --version)."
  echo "Install a modern Node (e.g. via fnm/nvm or NodeSource) and retry."
  exit 1
fi

command -v pnpm >/dev/null || { echo "pnpm is required (npm install -g pnpm)"; exit 1; }

# --- 2. Build the frontend (as the invoking user, using their Node) ----------
echo "==> Building frontend"
pushd "$PROJECT_ROOT/frontend" >/dev/null
pnpm install --frozen-lockfile || pnpm install
pnpm run build
popd >/dev/null

# --- 3. Create the service user (system account, no login) --------------------
if ! id "$APP_USER" >/dev/null 2>&1; then
  echo "==> Creating system user $APP_USER"
  sudo useradd --system --shell /usr/sbin/nologin --home-dir "$APP_DIR" "$APP_USER"
fi

# --- 4. Copy project into APP_DIR --------------------------------------------
echo "==> Copying project to $APP_DIR"
sudo mkdir -p "$APP_DIR" "$APP_DIR/data" "$APP_DIR/frontend"
sudo rsync -a --delete \
  --exclude '.venv' \
  --exclude 'node_modules' \
  --exclude '__pycache__' \
  --exclude '.pytest_cache' \
  --exclude '.hypothesis' \
  --exclude 'data' \
  "$PROJECT_ROOT/backend" "$PROJECT_ROOT/config.example.yaml" \
  "$PROJECT_ROOT/README.md" "$APP_DIR/"

# The built SPA must sit at APP_DIR/frontend/dist for main.py to find it.
sudo rsync -a --delete "$PROJECT_ROOT/frontend/dist/" "$APP_DIR/frontend/dist/"

# Preserve an existing config.yaml; otherwise seed from the example.
if [ ! -f "$APP_DIR/config.yaml" ]; then
  echo "==> No config.yaml found; seeding from config.example.yaml"
  echo "    EDIT $APP_DIR/config.yaml with real connection parameters before use."
  sudo cp "$PROJECT_ROOT/config.example.yaml" "$APP_DIR/config.yaml"
fi

# --- 5. Python virtualenv -----------------------------------------------------
echo "==> Setting up Python virtualenv"
sudo python3 -m venv "$APP_DIR/backend/.venv"
sudo "$APP_DIR/backend/.venv/bin/pip" install --upgrade pip
sudo "$APP_DIR/backend/.venv/bin/pip" install -r "$APP_DIR/backend/requirements.txt"

# --- 6. Permissions -----------------------------------------------------------
sudo chown -R "$APP_USER":"$APP_USER" "$APP_DIR"
sudo chmod 640 "$APP_DIR/config.yaml"   # config may contain secrets

# --- 7. Install and start the systemd service --------------------------------
echo "==> Installing systemd unit"
sudo cp "$SCRIPT_DIR/$SERVICE_NAME.service" "/etc/systemd/system/$SERVICE_NAME.service"
sudo systemctl daemon-reload
sudo systemctl enable "$SERVICE_NAME"

echo
echo "============================================================"
echo "Install complete."
echo
echo "Next steps:"
echo "  1. Edit the config:   sudo nano $APP_DIR/config.yaml"
echo "  2. Start the service: sudo systemctl restart $SERVICE_NAME"
echo "  3. Check status:      sudo systemctl status $SERVICE_NAME"
echo "  4. Follow logs:       journalctl -u $SERVICE_NAME -f"
echo
echo "The app will be available on http://<server>:8000"
echo "============================================================"
