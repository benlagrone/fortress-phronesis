#!/usr/bin/env bash
# Backup and replace the calculator.askmortgageauthority.com vhost to proxy the calculators container.
# Uses HTTP only; run certbot separately after DNS is in place to add SSL.

set -euo pipefail

VHOST="/etc/nginx/sites-available/calculator.askmortgageauthority.com"
BACKUP="${VHOST}.bak.$(date +%Y%m%d%H%M%S)"

cat <<'CONF' | sudo tee "${VHOST}.new" >/dev/null
server {
    listen 80;
    server_name calculator.askmortgageauthority.com;

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
sudo ln -sf "${VHOST}" "/etc/nginx/sites-enabled/calculator.askmortgageauthority.com"

echo "Testing nginx config"
sudo nginx -t

echo "Reloading nginx"
sudo nginx -s reload

echo "Done. Verify:"
echo "  curl -I http://127.0.0.1:18010"
echo "  curl -I http://calculator.askmortgageauthority.com"
echo "After DNS points here, run certbot for SSL and re-add ssl_certificate directives."
