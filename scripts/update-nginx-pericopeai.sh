#!/usr/bin/env bash
# Backup and replace the active pericopeai nginx vhost so public traffic points
# at the containerized frontend/API. Assumes container ports: API 18000, FE 13080.

set -euo pipefail

resolve_pericope_vhost_paths() {
  local enabled_candidate=""
  local available_candidate=""
  local resolved_target=""

  for candidate in \
    /etc/nginx/sites-enabled/pericopeai.com \
    /etc/nginx/sites-enabled/pericopeai.conf; do
    if sudo test -e "${candidate}"; then
      enabled_candidate="${candidate}"
      break
    fi
  done

  if [ -n "${enabled_candidate}" ]; then
    resolved_target="$(sudo readlink -f "${enabled_candidate}" 2>/dev/null || true)"
    if [ -n "${resolved_target}" ] && sudo test -e "${resolved_target}"; then
      printf '%s\n%s\n' "${enabled_candidate}" "${resolved_target}"
      return 0
    fi
    printf '%s\n%s\n' "${enabled_candidate}" "${enabled_candidate}"
    return 0
  fi

  for candidate in \
    /etc/nginx/sites-available/pericopeai.com \
    /etc/nginx/sites-available/pericopeai.conf; do
    if sudo test -e "${candidate}"; then
      available_candidate="${candidate}"
      break
    fi
  done

  if [ -z "${available_candidate}" ]; then
    available_candidate="/etc/nginx/sites-available/pericopeai.com"
  fi

  printf '%s\n%s\n' "/etc/nginx/sites-enabled/$(basename "${available_candidate}")" "${available_candidate}"
}

mapfile -t VHOST_PATHS < <(resolve_pericope_vhost_paths)
ACTIVE_LINK="${VHOST_PATHS[0]}"
VHOST="${VHOST_PATHS[1]}"
TIMESTAMP="$(date +%Y%m%d%H%M%S)"
BACKUP="${VHOST}.bak.${TIMESTAMP}"
ACTIVE_LINK_BACKUP="${ACTIVE_LINK}.bak.${TIMESTAMP}"

echo "Resolved Pericope vhost:"
echo "  active link: ${ACTIVE_LINK}"
echo "  config file: ${VHOST}"

sudo install -d -m 755 "$(dirname "${VHOST}")" "$(dirname "${ACTIVE_LINK}")"

cat <<'CONF' | sudo tee "${VHOST}.new" >/dev/null
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

if sudo test -e "${VHOST}"; then
  echo "Backing up ${VHOST} to ${BACKUP}"
  sudo cp "${VHOST}" "${BACKUP}"
fi

echo "Replacing ${VHOST}"
sudo mv "${VHOST}.new" "${VHOST}"

if [ "${ACTIVE_LINK}" != "${VHOST}" ]; then
  if sudo test -e "${ACTIVE_LINK}" && ! sudo test -L "${ACTIVE_LINK}"; then
    echo "Backing up non-symlink active site ${ACTIVE_LINK} to ${ACTIVE_LINK_BACKUP}"
    sudo cp "${ACTIVE_LINK}" "${ACTIVE_LINK_BACKUP}"
    sudo rm -f "${ACTIVE_LINK}"
  fi
  echo "Linking ${ACTIVE_LINK} -> ${VHOST}"
  sudo ln -sfn "${VHOST}" "${ACTIVE_LINK}"
fi

echo "Testing nginx config"
sudo nginx -t

echo "Reloading nginx"
sudo nginx -s reload

echo "Enabled site targets:"
sudo ls -l /etc/nginx/sites-enabled | grep 'pericopeai' || true

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
