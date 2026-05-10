#!/usr/bin/env bash
# Backup and replace the active pericopeai nginx vhost so public traffic points
# at the containerized frontend/API. Assumes container ports: API 18000, FE 13080.

set -euo pipefail

TIMESTAMP="$(date +%Y%m%d%H%M%S)"
CANONICAL_VHOST="/etc/nginx/sites-available/000-pericopeai-managed.conf"
CANONICAL_LINK="/etc/nginx/sites-enabled/000-pericopeai-managed.conf"
CANONICAL_BACKUP="${CANONICAL_VHOST}.bak.${TIMESTAMP}"

sudo install -d -m 755 "$(dirname "${CANONICAL_VHOST}")" "$(dirname "${CANONICAL_LINK}")"

cat <<'CONF' | sudo tee "${CANONICAL_VHOST}.new" >/dev/null
upstream pericope_api { server 127.0.0.1:18000; }
upstream pericope_fe  { server 127.0.0.1:13080; }

server {
    listen 80;
    listen [::]:80;
    listen 443 ssl;
    listen [::]:443 ssl;
    server_name pericopeai.com www.pericopeai.com;

    ssl_certificate /etc/letsencrypt/live/pericopeai.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/pericopeai.com/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;

    location = /api/pericope/guided-prompts {
        proxy_pass http://pericope_fe;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /api {
        proxy_pass http://pericope_api;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Authorization $http_authorization;
        # Cold-start requests (index/model warmup) can exceed nginx defaults.
        proxy_connect_timeout 10s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }

    location / {
        proxy_pass http://pericope_fe;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
CONF

if sudo test -e "${CANONICAL_VHOST}"; then
  echo "Backing up ${CANONICAL_VHOST} to ${CANONICAL_BACKUP}"
  sudo cp "${CANONICAL_VHOST}" "${CANONICAL_BACKUP}"
fi

echo "Writing canonical managed vhost ${CANONICAL_VHOST}"
sudo mv "${CANONICAL_VHOST}.new" "${CANONICAL_VHOST}"

shopt -s nullglob
for legacy in /etc/nginx/sites-enabled/*pericopeai* /etc/nginx/conf.d/*pericopeai*; do
  if [ "${legacy}" = "${CANONICAL_LINK}" ] || [ "${legacy}" = "${CANONICAL_VHOST}" ]; then
    continue
  fi
  backup="${legacy}.disabled.${TIMESTAMP}"
  echo "Disabling legacy Pericope config ${legacy} -> ${backup}"
  if sudo test -L "${legacy}"; then
    sudo rm -f "${legacy}"
  else
    sudo mv "${legacy}" "${backup}"
  fi
done
shopt -u nullglob

echo "Linking ${CANONICAL_LINK} -> ${CANONICAL_VHOST}"
sudo ln -sfn "${CANONICAL_VHOST}" "${CANONICAL_LINK}"

echo "Testing nginx config"
sudo nginx -t

echo "Reloading nginx"
sudo nginx -s reload

echo "Enabled site targets:"
sudo ls -l /etc/nginx/sites-enabled | grep 'pericopeai' || true

echo "Pericope config files:"
sudo find /etc/nginx/sites-available /etc/nginx/sites-enabled /etc/nginx/conf.d -maxdepth 1 \
  \( -name '*pericopeai*' -o -name '000-pericopeai-managed.conf' \) -print 2>/dev/null | sort || true

echo "Pericope server block excerpt:"
sudo nginx -T 2>&1 | awk '
  /server_name pericopeai\.com www\.pericopeai\.com;/ {capture=1}
  capture {print}
  capture && /^}/ {exit}
' || true

echo "Done. To verify:"
echo "  curl -I http://127.0.0.1:18000/docs   # API"
echo "  curl -I http://127.0.0.1:13080       # FE"
echo "  curl -I https://pericopeai.com/api"
echo "  curl -I https://pericopeai.com"
