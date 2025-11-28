#!/usr/bin/env bash
# Backup existing calculators vhost and replace with proxy to container on 127.0.0.1:18010.

set -euo pipefail

VHOST="/etc/nginx/sites-available/calculators.askmortgageauthority.com"
BACKUP="${VHOST}.bak.$(date +%Y%m%d%H%M%S)"

cat <<'CONF' | sudo tee "${VHOST}.new" >/dev/null
server {
    listen 80;
    listen 443 ssl;
    server_name calculators.askmortgageauthority.com;

    ssl_certificate /etc/letsencrypt/live/calculators.askmortgageauthority.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/calculators.askmortgageauthority.com/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;

    location / {
        proxy_pass http://127.0.0.1:18010;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
CONF

echo "Backing up ${VHOST} to ${BACKUP}"
if [ -f "${VHOST}" ]; then
  sudo cp "${VHOST}" "${BACKUP}"
fi

echo "Replacing ${VHOST}"
sudo mv "${VHOST}.new" "${VHOST}"

echo "Enabling site (symlink)"
if [ ! -L "/etc/nginx/sites-enabled/calculators.askmortgageauthority.com" ]; then
  sudo ln -s "${VHOST}" "/etc/nginx/sites-enabled/calculators.askmortgageauthority.com"
fi

echo "Testing nginx config"
sudo nginx -t

echo "Reloading nginx"
sudo nginx -s reload

echo "Done. Verify:"
echo "  curl -I http://127.0.0.1:18010"
echo "  curl -I https://calculators.askmortgageauthority.com"
