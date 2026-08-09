#!/usr/bin/env bash
# Deploy / update the app on the VPS and restart gunicorn.
#
# First-time server prep (once):
#   sudo adduser --disabled-password --gecos "" deploy
#   sudo usermod -aG www-data deploy
#   sudo mkdir -p /var/www/itsfreerealestate
#   sudo chown deploy:www-data /var/www/itsfreerealestate
#   sudo -u deploy git clone <repo-url> /var/www/itsfreerealestate
#   cd /var/www/itsfreerealestate
#   sudo -u deploy python3 -m venv .venv
#   sudo -u deploy cp deploy/env.example .env   # then edit secrets / hosts
#   # Match User= in the unit files to your Linux deploy account if not "deploy"
#   sudo cp deploy/itsfreerealestate.service /etc/systemd/system/
#   sudo cp deploy/itsfreerealestate-scrape.service /etc/systemd/system/
#   sudo cp deploy/itsfreerealestate-scrape.timer /etc/systemd/system/
#   sudo cp deploy/nginx.itsfreerealestate.am.conf /etc/nginx/sites-available/itsfreerealestate.am
#   sudo ln -sf /etc/nginx/sites-available/itsfreerealestate.am /etc/nginx/sites-enabled/
#   # passwordless restart for deploy user:
#   echo 'deploy ALL=(root) NOPASSWD: /bin/systemctl restart itsfreerealestate, /bin/systemctl status itsfreerealestate' | sudo tee /etc/sudoers.d/itsfreerealestate
#   sudo systemctl daemon-reload
#   sudo systemctl enable --now itsfreerealestate
#   sudo systemctl enable --now itsfreerealestate-scrape.timer
#   sudo nginx -t && sudo systemctl reload nginx
#   # TLS: sudo certbot --nginx -d itsfreerealestate.am -d www.itsfreerealestate.am
#
# Then run this script after each release:
#   ./deploy/deploy.sh

set -euo pipefail

APP_DIR="${APP_DIR:-/var/www/itsfreerealestate}"
SERVICE_NAME="${SERVICE_NAME:-itsfreerealestate}"
BRANCH="${DEPLOY_BRANCH:-main}"

cd "$APP_DIR"

if [[ ! -f .env ]]; then
  echo "Missing $APP_DIR/.env — copy deploy/env.example and fill in values." >&2
  exit 1
fi

# Export env for manage.py / gunicorn child processes started later by systemd
# (systemd unit also loads EnvironmentFile=.env).
set -a
# shellcheck disable=SC1091
source .env
set +a

echo "==> Fetching $BRANCH"
git fetch --prune origin
git checkout "$BRANCH"
git reset --hard "origin/$BRANCH"

if [[ ! -d .venv ]]; then
  python3 -m venv .venv
fi

echo "==> Installing dependencies"
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt

echo "==> Django migrate / collectstatic"
.venv/bin/python manage.py migrate --noinput
.venv/bin/python manage.py collectstatic --noinput

echo "==> Restarting $SERVICE_NAME"
sudo systemctl restart "$SERVICE_NAME"
sudo systemctl --no-pager --full status "$SERVICE_NAME" | head -n 20

echo "==> Deploy finished"
