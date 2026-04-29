#!/usr/bin/env bash
# Bootstrap and maintain the assets.pericopeai.com nginx vhost for the shared asset container.
# Assumes the container is bound on 127.0.0.1:13085.

set -euo pipefail

DOMAIN="assets.pericopeai.com"
UPSTREAM="127.0.0.1:13085"
VHOST="/etc/nginx/sites-available/${DOMAIN}"
ENABLED="/etc/nginx/sites-enabled/${DOMAIN}"
CERT_DIR="/etc/letsencrypt/live/${DOMAIN}"
LE_EMAIL="${LETSENCRYPT_EMAIL:-}"

render_http_only() {
  cat <<CONF
upstream pericopeai_assets { server ${UPSTREAM}; }

server {
    listen 80;
    server_name ${DOMAIN};

    location / {
        proxy_pass http://pericopeai_assets;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
CONF
}

render_https() {
  cat <<CONF
upstream pericopeai_assets { server ${UPSTREAM}; }

server {
    listen 80;
    server_name ${DOMAIN};
    return 301 https://\$host\$request_uri;
}

server {
    listen 443 ssl;
    server_name ${DOMAIN};

    ssl_certificate ${CERT_DIR}/fullchain.pem;
    ssl_certificate_key ${CERT_DIR}/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;

    location / {
        proxy_pass http://pericopeai_assets;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
CONF
}

write_vhost() {
  local mode="$1"
  local tmp
  tmp="$(mktemp)"
  if [ "$mode" = "http" ]; then
    render_http_only > "$tmp"
  else
    render_https > "$tmp"
  fi
  sudo mv "$tmp" "$VHOST"
  if [ ! -e "$ENABLED" ]; then
    sudo ln -s "$VHOST" "$ENABLED"
  fi
}

reload_nginx() {
  sudo nginx -t
  if command -v systemctl >/dev/null 2>&1; then
    sudo systemctl reload nginx
  else
    sudo nginx -s reload
  fi
}

ensure_certificate() {
  if [ -f "${CERT_DIR}/fullchain.pem" ] && [ -f "${CERT_DIR}/privkey.pem" ]; then
    return 0
  fi

  local certbot_args=(--nginx -d "${DOMAIN}" --non-interactive --agree-tos)
  if [ -n "${LE_EMAIL}" ]; then
    certbot_args+=(--email "${LE_EMAIL}")
  else
    certbot_args+=(--register-unsafely-without-email)
  fi

  sudo certbot "${certbot_args[@]}"
}

write_vhost http
reload_nginx
ensure_certificate
write_vhost https
reload_nginx

echo "Done. To verify:"
echo "  curl -I http://${DOMAIN}/healthz"
echo "  curl -I https://${DOMAIN}/healthz"
echo "  curl -I http://${UPSTREAM}/healthz"
echo "  curl -I http://${UPSTREAM}/scriptorium-icons/v1/manifest.json"
