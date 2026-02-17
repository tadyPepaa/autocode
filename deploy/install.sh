#!/bin/bash
set -euo pipefail

APP_DIR="/opt/autocode"
REPO_URL="https://github.com/your-org/autocode.git"
BRANCH="main"
SERVICE_NAME="autocode"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

# --- Pre-flight checks ---

if [[ $EUID -ne 0 ]]; then
    echo "This script must be run as root" >&2
    exit 1
fi

# --- Create user ---

if ! id -u "$SERVICE_NAME" &>/dev/null; then
    log "Creating user $SERVICE_NAME..."
    useradd --system --shell /usr/sbin/nologin --home-dir "$APP_DIR" "$SERVICE_NAME"
fi

# --- Directory structure ---

log "Setting up directories..."
mkdir -p "$APP_DIR"/{data,frontend,backend}
chown -R "$SERVICE_NAME":"$SERVICE_NAME" "$APP_DIR"

# --- Clone or update repo ---

if [[ -d "$APP_DIR/repo/.git" ]]; then
    log "Updating repository..."
    cd "$APP_DIR/repo"
    git fetch origin "$BRANCH"
    git reset --hard "origin/$BRANCH"
else
    log "Cloning repository..."
    git clone --branch "$BRANCH" "$REPO_URL" "$APP_DIR/repo"
fi

# --- Backend setup ---

log "Setting up backend..."
cp -r "$APP_DIR/repo/backend/"* "$APP_DIR/backend/"

if command -v uv &>/dev/null; then
    log "Using uv for Python environment..."
    cd "$APP_DIR/backend"
    uv venv .venv
    uv pip install -r requirements.txt --python .venv/bin/python
else
    log "Using pip for Python environment..."
    cd "$APP_DIR/backend"
    python3 -m venv .venv
    .venv/bin/pip install --upgrade pip
    .venv/bin/pip install -r requirements.txt
fi

# --- Frontend build ---

log "Building frontend..."
cd "$APP_DIR/repo/frontend"

if ! command -v node &>/dev/null; then
    echo "Node.js is required but not installed" >&2
    exit 1
fi

npm ci
npm run build
rm -rf "$APP_DIR/frontend/dist"
cp -r dist "$APP_DIR/frontend/dist"

# --- Fix ownership ---

chown -R "$SERVICE_NAME":"$SERVICE_NAME" "$APP_DIR"

# --- Install systemd service ---

log "Installing systemd service..."
cp "$APP_DIR/repo/deploy/autocode.service" /etc/systemd/system/"$SERVICE_NAME".service
systemctl daemon-reload
systemctl enable "$SERVICE_NAME"

# --- Start / restart service ---

if systemctl is-active --quiet "$SERVICE_NAME"; then
    log "Restarting $SERVICE_NAME..."
    systemctl restart "$SERVICE_NAME"
else
    log "Starting $SERVICE_NAME..."
    systemctl start "$SERVICE_NAME"
fi

log "Done. Service status:"
systemctl status "$SERVICE_NAME" --no-pager
