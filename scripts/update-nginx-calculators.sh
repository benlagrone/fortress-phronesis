#!/usr/bin/env bash
# Backup existing calculators vhost and replace with proxy to container on 127.0.0.1:18010.

set -euo pipefail

VHOST="/etc/nginx/sites-available/calculators.askmortgageauthority.com"
BACKUP="${VHOST}.bak.$(date +%Y%m%d%H%M%S)"

# Write HTTP-only vhost; add SSL after cert is issued.
cat <<'CONF' | sudo tee "${VHOST}.new" >/dev/null
server {
    listen 80;
    server_name calculators.askmortgageauthority.com;

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
echo "  curl -I http://calculators.askmortgageauthority.com"
echo "After DNS and cert issuance, reintroduce ssl_certificate directives for HTTPS."
