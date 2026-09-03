#!/usr/bin/env bash
set -euo pipefail

# Weaver deploy script
# Usage:
#  sudo ./deploy.sh --repo <git-url> --branch main --domain example.com --email admin@example.com
# Or run without --repo if the app is already present under /srv/weaver/app

REPO_URL=""
BRANCH="main"
DEPLOY_DIR="/srv/weaver"
APP_DIR="$DEPLOY_DIR/app"
VENV_DIR="$DEPLOY_DIR/.venv"
ENV_FILE="/etc/weaver/weaver.env"
DOMAIN=""
EMAIL=""
RUN_CERTBOT="no"

usage(){
  cat <<EOF
Usage: sudo $0 [--repo <git-url>] [--branch <branch>] [--deploy-dir <path>] [--domain <domain>] [--email <email>] [--certbot yes|no]

If --repo is omitted this assumes the code is already at ${APP_DIR} (e.g. by CI or rsync).
If --certbot yes you must provide --domain and --email to request a TLS certificate.
EOF
  exit 1
}

while [[ ${#} -gt 0 ]]; do
  case "$1" in
    --repo) REPO_URL="$2"; shift 2;;
    --branch) BRANCH="$2"; shift 2;;
    --deploy-dir) DEPLOY_DIR="$2"; APP_DIR="$DEPLOY_DIR/app"; VENV_DIR="$DEPLOY_DIR/.venv"; shift 2;;
    --env-file) ENV_FILE="$2"; shift 2;;
    --domain) DOMAIN="$2"; shift 2;;
    --email) EMAIL="$2"; shift 2;;
    --certbot) RUN_CERTBOT="$2"; shift 2;;
    -h|--help) usage;;
    *) echo "Unknown arg: $1"; usage;;
  esac
done

if [[ $(id -u) -ne 0 ]]; then
  echo "This script must be run as root (sudo)." >&2
  exit 2
fi

echo "Deploy configuration:" 
echo "  REPO_URL=${REPO_URL:-(none)}"
echo "  BRANCH=${BRANCH}"
echo "  DEPLOY_DIR=${DEPLOY_DIR}"
echo "  APP_DIR=${APP_DIR}"
echo "  VENV_DIR=${VENV_DIR}"
echo "  ENV_FILE=${ENV_FILE}"
echo "  DOMAIN=${DOMAIN:-(none)}"
echo "  RUN_CERTBOT=${RUN_CERTBOT}"

# Create deploy user if not exists
if ! id -u weaver >/dev/null 2>&1; then
  echo "Creating system user 'weaver'"
  useradd --system --no-create-home --shell /usr/sbin/nologin weaver || true
fi

mkdir -p "$DEPLOY_DIR" "$APP_DIR" /var/log/weaver /etc/weaver
chown -R weaver:weaver "$DEPLOY_DIR" /var/log/weaver /etc/weaver
chmod 750 /etc/weaver

if [[ -n "$REPO_URL" ]]; then
  echo "Cloning or updating repo into ${APP_DIR}"
  if [[ -d "$APP_DIR/.git" ]]; then
    sudo -u weaver git -C "$APP_DIR" fetch --all --prune
    sudo -u weaver git -C "$APP_DIR" checkout "$BRANCH"
    sudo -u weaver git -C "$APP_DIR" pull --ff-only origin "$BRANCH"
  else
    sudo -u weaver git clone --depth 1 --branch "$BRANCH" "$REPO_URL" "$APP_DIR"
  fi
fi

if [[ ! -f "$APP_DIR/requirements.txt" ]]; then
  echo "No requirements.txt found in ${APP_DIR}; aborting." >&2
  exit 3
fi

echo "Creating virtualenv and installing requirements"
sudo -u weaver bash -lc "python3 -m venv '${VENV_DIR}'"
sudo -u weaver bash -lc "'${VENV_DIR}/bin/python' -m pip install --upgrade pip setuptools wheel"
sudo -u weaver bash -lc "'${VENV_DIR}/bin/pip' install -r '${APP_DIR}/requirements.txt'"

# Ensure env file exists; create minimal if missing
if [[ ! -f "$ENV_FILE" ]]; then
  echo "Creating minimal ${ENV_FILE} with generated SECRET_KEY. Edit to add DB/REDIS values."
  SECRET_KEY=$(openssl rand -hex 32)
  cat > "$ENV_FILE" <<EOF
SECRET_KEY=${SECRET_KEY}
ENV=production
FORCE_HTTPS=true
EOF
  chown weaver:weaver "$ENV_FILE"
  chmod 600 "$ENV_FILE"
  echo "Created ${ENV_FILE}; please edit to add MONGO_URI, REDIS_URL, and other secrets before starting the service." 
fi

# Install systemd unit
if [[ -f "$APP_DIR/deploy/weaver.service" ]]; then
  echo "Installing systemd unit"
  cp "$APP_DIR/deploy/weaver.service" /etc/systemd/system/weaver.service
fi

systemctl daemon-reload
systemctl enable --now weaver || true
systemctl restart weaver || true

echo "Service status:"
systemctl status --no-pager weaver || true

# Install nginx site
if [[ -f "$APP_DIR/deploy/nginx-weaver.conf" ]]; then
  echo "Installing nginx site configuration"
  cp "$APP_DIR/deploy/nginx-weaver.conf" /etc/nginx/sites-available/weaver.conf
  ln -fs /etc/nginx/sites-available/weaver.conf /etc/nginx/sites-enabled/weaver.conf
  nginx -t && systemctl reload nginx || true
fi

# Optional: request certbot cert if requested
if [[ "$RUN_CERTBOT" = "yes" || "$RUN_CERTBOT" = "y" ]]; then
  if [[ -z "$DOMAIN" || -z "$EMAIL" ]]; then
    echo "To run certbot provide --domain and --email" >&2
  else
    echo "Requesting TLS cert for ${DOMAIN} using certbot (non-interactive)"
    certbot --nginx -d "$DOMAIN" -m "$EMAIL" --agree-tos --non-interactive || true
    nginx -t && systemctl reload nginx || true
  fi
fi

echo "Deployment finished. Verify the app and logs."
echo "Check service logs: sudo journalctl -u weaver -f"
echo "Check local health: curl -I http://127.0.0.1:8000/health"
echo "If you enabled certbot, test: curl -I https://${DOMAIN}/health"

exit 0
