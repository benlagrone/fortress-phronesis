#!/usr/bin/env bash
# Backup and replace the askmortgageauthority.com vhost to proxy WordPress container on 127.0.0.1:18020.

set -euo pipefail

VHOST="/etc/nginx/sites-available/askmortgageauthority.com"
BACKUP="${VHOST}.bak.$(date +%Y%m%d%H%M%S)"

cat <<'CONF' | sudo tee "${VHOST}.new" >/dev/null
upstream ama_wp {
    server 127.0.0.1:18020;
}

server {
    listen 80;
    listen 443 ssl;
    server_name askmortgageauthority.com www.askmortgageauthority.com;

    # TODO: ensure these cert paths exist for this domain
    ssl_certificate /etc/letsencrypt/live/askmortgageauthority.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/askmortgageauthority.com/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;

    location / {
        proxy_pass http://ama_wp;
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
sudo ln -sf "${VHOST}" "/etc/nginx/sites-enabled/askmortgageauthority.com"

echo "Testing nginx config"
sudo nginx -t

echo "Reloading nginx"
sudo nginx -s reload

echo "Done. Verify:"
echo "  curl -I http://127.0.0.1:18020"
echo "  curl -I https://askmortgageauthority.com"
echo "Backup saved at ${BACKUP}"
