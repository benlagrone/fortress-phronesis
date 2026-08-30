#!/usr/bin/env bash
set -euo pipefail

PUBLIC_HOST="${RENTAL_FINDER_PUBLIC_HOST:-rentalfinder.lecrownproperties.com}"
PUBLIC_IP="${RENTAL_FINDER_PUBLIC_IP:-89.117.151.145}"
BACKEND_ORIGIN="${RENTAL_FINDER_BACKEND_ORIGIN:-http://100.100.97.30:8133}"
AUTH_PORT="${RENTAL_FINDER_AUTH_PORT:-18044}"
COMPOSE_PROJECT="${RENTAL_FINDER_COMPOSE_PROJECT:-rental-finder-edge}"
DEPLOY_ROOT="${RENTAL_FINDER_DEPLOY_ROOT:-/opt/rental-finder/deploy}"
OAUTH_ENV_FILE="${RENTAL_FINDER_OAUTH_ENV_FILE:-/opt/rental-finder/env/google-oauth.prod.env}"
OAUTH_ENV_SOURCE="${RENTAL_FINDER_OAUTH_ENV_SOURCE:-}"
CERTBOT_EMAIL="${RENTAL_FINDER_CERTBOT_EMAIL:-admin@lecrownproperties.com}"
BOOTSTRAP_ONLY="${RENTAL_FINDER_BOOTSTRAP_ONLY:-false}"
ACME_WEBROOT="${RENTAL_FINDER_ACME_WEBROOT:-/var/www/letsencrypt}"
NGINX_SITE="/etc/nginx/sites-available/${PUBLIC_HOST}"
NGINX_LINK="/etc/nginx/sites-enabled/${PUBLIC_HOST}"

log() {
  printf '==> %s\n' "$*"
}

fail() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || fail "Required command is missing: $1"
}

if [ "$(id -u)" -ne 0 ]; then
  fail "Rental Finder edge deployment must run as root."
fi

for command_name in curl nginx certbot getent; do
  require_command "${command_name}"
done

if [ "${BOOTSTRAP_ONLY}" != "true" ]; then
  require_command docker
fi

SCRIPT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SOURCE_COMPOSE_FILE="${SCRIPT_ROOT}/docker-compose.rental-finder.yml"
install -d -m 755 "${DEPLOY_ROOT}" "$(dirname "${OAUTH_ENV_FILE}")" "${ACME_WEBROOT}"

if [ "${BOOTSTRAP_ONLY}" != "true" ]; then
  [ -f "${SOURCE_COMPOSE_FILE}" ] || fail "Missing compose file: ${SOURCE_COMPOSE_FILE}"

  log "Checking the private Fortress Rental Finder upstream before changing the edge"
  backend_html="$(curl -fsS --max-time 15 "${BACKEND_ORIGIN}/rental-finder/")" \
    || fail "Private Rental Finder upstream is unavailable at ${BACKEND_ORIGIN}/rental-finder/."
  printf '%s' "${backend_html}" | grep -q '<title>Rental Finder</title>' \
    || fail "Private upstream did not return the expected Rental Finder page."

  install -m 644 "${SOURCE_COMPOSE_FILE}" "${DEPLOY_ROOT}/docker-compose.rental-finder.yml"

  if [ -n "${OAUTH_ENV_SOURCE}" ]; then
    [ -f "${OAUTH_ENV_SOURCE}" ] || fail "OAuth environment source does not exist."
    install -m 600 "${OAUTH_ENV_SOURCE}" "${OAUTH_ENV_FILE}"
    rm -f "${OAUTH_ENV_SOURCE}"
  fi

  [ -s "${OAUTH_ENV_FILE}" ] || fail "OAuth environment file is missing: ${OAUTH_ENV_FILE}"
  for name in RENTAL_FINDER_GOOGLE_CLIENT_ID RENTAL_FINDER_GOOGLE_CLIENT_SECRET RENTAL_FINDER_OAUTH_COOKIE_SECRET; do
    grep -q "^${name}=." "${OAUTH_ENV_FILE}" || fail "OAuth environment file is missing ${name}."
  done
  chmod 600 "${OAUTH_ENV_FILE}"

  compose=(docker compose --env-file "${OAUTH_ENV_FILE}" -p "${COMPOSE_PROJECT}" -f "${DEPLOY_ROOT}/docker-compose.rental-finder.yml")
  "${compose[@]}" config --quiet

  log "Starting the loopback-only Google OAuth gateway"
  "${compose[@]}" pull rental-finder-auth
  "${compose[@]}" up -d rental-finder-auth

  for attempt in $(seq 1 20); do
    if curl -fsS --max-time 3 "http://127.0.0.1:${AUTH_PORT}/ping" >/dev/null; then
      break
    fi
    if [ "${attempt}" -eq 20 ]; then
      "${compose[@]}" logs --tail=80 rental-finder-auth >&2 || true
      fail "OAuth gateway did not become healthy."
    fi
    sleep 1
  done
fi

install -d -m 755 /etc/nginx/sites-available /etc/nginx/sites-enabled
backup_site=""
if [ -f "${NGINX_SITE}" ]; then
  backup_site="${NGINX_SITE}.bak.$(date +%Y%m%d%H%M%S)"
  cp "${NGINX_SITE}" "${backup_site}"
fi

rollback_nginx() {
  if [ -n "${backup_site}" ] && [ -f "${backup_site}" ]; then
    cp "${backup_site}" "${NGINX_SITE}"
    ln -sfn "${NGINX_SITE}" "${NGINX_LINK}"
  else
    rm -f "${NGINX_SITE}" "${NGINX_LINK}"
  fi
  nginx -t >/dev/null 2>&1 && { systemctl reload nginx || nginx -s reload; } || true
}

write_http_bootstrap() {
  cat >"${NGINX_SITE}.new" <<NGINX
server {
    listen 80;
    server_name ${PUBLIC_HOST};

    location ^~ /.well-known/acme-challenge/ {
        root ${ACME_WEBROOT};
        default_type "text/plain";
    }

    location / {
        default_type "text/plain";
        return 503 "Rental Finder is waiting for DNS and TLS activation.\n";
    }
}
NGINX
  mv "${NGINX_SITE}.new" "${NGINX_SITE}"
  ln -sfn "${NGINX_SITE}" "${NGINX_LINK}"
}

write_https_site() {
  cat >"${NGINX_SITE}.new" <<NGINX
server {
    listen 80;
    server_name ${PUBLIC_HOST};

    location ^~ /.well-known/acme-challenge/ {
        root ${ACME_WEBROOT};
        default_type "text/plain";
    }

    location / {
        return 301 https://\$host\$request_uri;
    }
}

server {
    listen 443 ssl http2;
    server_name ${PUBLIC_HOST};

    ssl_certificate /etc/letsencrypt/live/${PUBLIC_HOST}/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/${PUBLIC_HOST}/privkey.pem;

    add_header Cache-Control "no-store" always;
    add_header Referrer-Policy "same-origin" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "DENY" always;
    client_max_body_size 2m;

    location /oauth2/ {
        proxy_pass http://127.0.0.1:${AUTH_PORT};
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Host \$host;
        proxy_set_header X-Forwarded-Proto https;
    }

    location = /_oauth2_auth {
        internal;
        proxy_pass http://127.0.0.1:${AUTH_PORT}/oauth2/auth;
        proxy_pass_request_body off;
        proxy_set_header Content-Length "";
        proxy_set_header X-Original-URL \$scheme://\$http_host\$request_uri;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Host \$host;
        proxy_set_header X-Forwarded-Proto https;
    }

    location @oauth2_signin {
        return 302 /oauth2/start?rd=\$scheme://\$http_host\$request_uri;
    }

    location ^~ /rental-finder/api/ {
        auth_request /_oauth2_auth;
        error_page 401 = @oauth2_signin;
        auth_request_set \$authenticated_user \$upstream_http_x_auth_request_user;
        auth_request_set \$authenticated_email \$upstream_http_x_auth_request_email;

        proxy_pass ${BACKEND_ORIGIN};
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header Authorization "";
        proxy_set_header X-Authenticated-User \$authenticated_user;
        proxy_set_header X-Authenticated-Email \$authenticated_email;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Host \$host;
        proxy_set_header X-Forwarded-Proto https;
        proxy_read_timeout 180s;
    }

    location / {
        auth_request /_oauth2_auth;
        error_page 401 = @oauth2_signin;
        auth_request_set \$authenticated_user \$upstream_http_x_auth_request_user;
        auth_request_set \$authenticated_email \$upstream_http_x_auth_request_email;

        proxy_pass ${BACKEND_ORIGIN}/rental-finder/;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header Authorization "";
        proxy_set_header X-Authenticated-User \$authenticated_user;
        proxy_set_header X-Authenticated-Email \$authenticated_email;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Host \$host;
        proxy_set_header X-Forwarded-Proto https;
        proxy_read_timeout 180s;
    }
}
NGINX
  mv "${NGINX_SITE}.new" "${NGINX_SITE}"
  ln -sfn "${NGINX_SITE}" "${NGINX_LINK}"
}

write_https_unavailable_site() {
  cat >"${NGINX_SITE}.new" <<NGINX
server {
    listen 80;
    server_name ${PUBLIC_HOST};

    location ^~ /.well-known/acme-challenge/ {
        root ${ACME_WEBROOT};
        default_type "text/plain";
    }

    location / {
        return 301 https://\$host\$request_uri;
    }
}

server {
    listen 443 ssl http2;
    server_name ${PUBLIC_HOST};

    ssl_certificate /etc/letsencrypt/live/${PUBLIC_HOST}/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/${PUBLIC_HOST}/privkey.pem;

    add_header Cache-Control "no-store" always;
    add_header Referrer-Policy "same-origin" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "DENY" always;

    location / {
        default_type "text/plain";
        return 503 "Rental Finder is temporarily unavailable while its private service is restored.\n";
    }
}
NGINX
  mv "${NGINX_SITE}.new" "${NGINX_SITE}"
  ln -sfn "${NGINX_SITE}" "${NGINX_LINK}"
}

log "Installing the fail-closed HTTP bootstrap"
write_http_bootstrap
if ! nginx -t; then
  rollback_nginx
  fail "Nginx rejected the Rental Finder bootstrap configuration."
fi
systemctl reload nginx || nginx -s reload

resolved_ip="$(getent ahostsv4 "${PUBLIC_HOST}" | awk '{print $1; exit}' || true)"
if [ "${resolved_ip}" != "${PUBLIC_IP}" ]; then
  fail "DNS for ${PUBLIC_HOST} resolves to '${resolved_ip:-none}', expected ${PUBLIC_IP}; HTTPS was not activated."
fi

log "Issuing or renewing the public TLS certificate"
certbot certonly --webroot -w "${ACME_WEBROOT}" -d "${PUBLIC_HOST}" \
  --non-interactive --agree-tos --email "${CERTBOT_EMAIL}" --keep-until-expiring

if [ "${BOOTSTRAP_ONLY}" = "true" ]; then
  write_https_unavailable_site
  if ! nginx -t; then
    rollback_nginx
    fail "Nginx rejected the fail-closed Rental Finder configuration."
  fi
  systemctl reload nginx || nginx -s reload

  unavailable_status=""
  for attempt in $(seq 1 10); do
    unavailable_status="$(curl --http1.1 --noproxy '*' -ksS -H "Host: ${PUBLIC_HOST}" -o /dev/null -w '%{http_code}' "https://127.0.0.1/")"
    [ "${unavailable_status}" = "503" ] && break
    sleep 1
  done
  [ "${unavailable_status}" = "503" ] || fail "Expected fail-closed site to return 503, got ${unavailable_status}."
  log "Rental Finder TLS is active and the edge is fail-closed until the private service and OAuth are ready."
  exit 0
fi

write_https_site
if ! nginx -t; then
  rollback_nginx
  fail "Nginx rejected the authenticated Rental Finder configuration."
fi
systemctl reload nginx || nginx -s reload

log "Verifying that unauthenticated UI and API requests cannot reach Fortress"
root_headers="$(mktemp)"
api_headers="$(mktemp)"
trap 'rm -f "${root_headers}" "${api_headers}"' EXIT

root_status="$(curl --http1.1 --noproxy '*' -ksS -H "Host: ${PUBLIC_HOST}" -D "${root_headers}" -o /dev/null -w '%{http_code}' "https://127.0.0.1/")"
[ "${root_status}" = "302" ] || fail "Expected unauthenticated UI request to return 302, got ${root_status}."
grep -qi '^location: /oauth2/start?' "${root_headers}" || fail "UI request did not redirect to the OAuth start route."

api_status="$(curl --http1.1 --noproxy '*' -ksS -H "Host: ${PUBLIC_HOST}" -D "${api_headers}" -o /dev/null -w '%{http_code}' "https://127.0.0.1/rental-finder/api/listings/search")"
[ "${api_status}" = "302" ] || fail "Expected unauthenticated API request to return 302, got ${api_status}."
grep -qi '^location: /oauth2/start?' "${api_headers}" || fail "API request did not redirect to the OAuth start route."

"${compose[@]}" ps rental-finder-auth
log "Rental Finder Google Workspace edge is active at https://${PUBLIC_HOST}/"
