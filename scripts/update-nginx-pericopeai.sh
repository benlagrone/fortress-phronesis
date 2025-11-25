#!/usr/bin/env bash
# Backup and replace the pericopeai.com nginx vhost to point at containerized frontend/API.
# Assumes container ports: API 18000, FE 13080.

set -euo pipefail

VHOST="/etc/nginx/sites-available/pericopeai.com"
BACKUP="${VHOST}.bak.$(date +%Y%m%d%H%M%S)"

cat <<'CONF' | sudo tee "${VHOST}.new" >/dev/null
upstream pericope_api { server 127.0.0.1:18000; }
upstream pericope_fe  { server 127.0.0.1:13080; }

server {
    listen 80;
    listen 443 ssl;
    server_name pericopeai.com www.pericopeai.com;

    ssl_certificate /etc/letsencrypt/live/pericopeai.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/pericopeai.com/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;

    location /api {
        proxy_pass http://pericope_api;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location / {
        proxy_pass http://pericope_fe;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
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
echo "  curl -I http://127.0.0.1:18000/docs   # API"
echo "  curl -I http://127.0.0.1:13080        # FE"
echo "  curl -I https://pericopeai.com/api"
echo "  curl -I https://pericopeai.com"
