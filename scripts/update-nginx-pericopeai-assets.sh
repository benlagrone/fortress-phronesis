#!/usr/bin/env bash
# Backup and replace the assets.pericopeai.com nginx vhost to point at the shared asset container.
# Assumes the container is bound on 127.0.0.1:13084.

set -euo pipefail

VHOST="/etc/nginx/sites-available/assets.pericopeai.com"
BACKUP="${VHOST}.bak.$(date +%Y%m%d%H%M%S)"

cat <<'CONF' | sudo tee "${VHOST}.new" >/dev/null
upstream pericopeai_assets { server 127.0.0.1:13084; }

server {
    listen 80;
    listen 443 ssl;
    server_name assets.pericopeai.com;

    ssl_certificate /etc/letsencrypt/live/assets.pericopeai.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/assets.pericopeai.com/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;

    location / {
        proxy_pass http://pericopeai_assets;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
CONF

echo "Backing up ${VHOST} to ${BACKUP}"
sudo cp "${VHOST}" "${BACKUP}"

echo "Replacing ${VHOST}"
sudo mv "${VHOST}.new" "${VHOST}"

echo "Testing nginx config"
sudo nginx -t

echo "Reloading nginx"
sudo nginx -s reload

echo "Done. To verify:"
echo "  curl -I http://127.0.0.1:13084/healthz"
echo "  curl -I http://127.0.0.1:13084/scriptorium-icons/v1/manifest.json"
echo "  curl -I https://assets.pericopeai.com/healthz"
echo "  curl -I https://assets.pericopeai.com/scriptorium-icons/v1/manifest.json"
