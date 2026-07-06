#!/usr/bin/env bash
set -euo pipefail

FORTRESS_DEPLOY_ROOT="${FORTRESS_DEPLOY_ROOT:-/root/workspace/Fortress}"
FORTRESS_COMPOSE_PROJECT="${FORTRESS_COMPOSE_PROJECT:-fortress-personal}"
FORTRESS_ENV_FILE="${FORTRESS_ENV_FILE:-${FORTRESS_DEPLOY_ROOT}/.env.contabo}"
FORTRESS_REMOTE_HOSTNAME="${FORTRESS_REMOTE_HOSTNAME:-fortress.benjaminlagrone.com}"
FORTRESS_LEGACY_TEMP_HOSTNAME="${FORTRESS_LEGACY_TEMP_HOSTNAME:-fortress.89-117-151-145.sslip.io}"
FORTRESS_PUBLIC_IP="${FORTRESS_PUBLIC_IP:-89.117.151.145}"
FORTRESS_BIND="${FORTRESS_BIND:-127.0.0.1}"
FORTRESS_WATCH_PORT="${FORTRESS_WATCH_PORT:-15173}"
FORTRESS_API_PORT="${FORTRESS_API_PORT:-18080}"
FORTRESS_BASIC_AUTH_USER="${FORTRESS_BASIC_AUTH_USER:-benjaminlagrone@gmail.com}"
FORTRESS_HTPASSWD_FILE="${FORTRESS_HTPASSWD_FILE:-/etc/nginx/fortress-phronesis.htpasswd}"
FORTRESS_CERTBOT_EMAIL="${FORTRESS_CERTBOT_EMAIL:-benjaminlagrone@gmail.com}"
ACME_WEBROOT="${ACME_WEBROOT:-/var/www/letsencrypt}"

log() {
  printf '==> %s\n' "$*"
}

require_file() {
  if [ ! -f "$1" ]; then
    printf 'Missing required file: %s\n' "$1" >&2
    exit 1
  fi
}

write_default_env() {
  cat >"${FORTRESS_ENV_FILE}" <<EOF_ENV
FORTRESS_BIND=${FORTRESS_BIND}
FORTRESS_WATCH_PORT=${FORTRESS_WATCH_PORT}
FORTRESS_API_PORT=${FORTRESS_API_PORT}
FORTRESS_LAN_HOSTNAME=phronesis.fortress.lan
FORTRESS_REMOTE_HOSTNAME=${FORTRESS_REMOTE_HOSTNAME}
EOF_ENV
  chmod 600 "${FORTRESS_ENV_FILE}"
}

ensure_basic_auth() {
  install -d "$(dirname "${FORTRESS_HTPASSWD_FILE}")"

  if [ -n "${FORTRESS_BASIC_AUTH_PASSWORD:-}" ]; then
    if command -v openssl >/dev/null 2>&1; then
      hash="$(openssl passwd -apr1 "${FORTRESS_BASIC_AUTH_PASSWORD}")"
    elif command -v htpasswd >/dev/null 2>&1; then
      tmp="$(mktemp)"
      htpasswd -Bbc "${tmp}" "${FORTRESS_BASIC_AUTH_USER}" "${FORTRESS_BASIC_AUTH_PASSWORD}" >/dev/null
      install -m 640 "${tmp}" "${FORTRESS_HTPASSWD_FILE}"
      rm -f "${tmp}"
      return
    else
      echo "Need openssl or htpasswd to update Basic Auth credentials." >&2
      exit 1
    fi
    printf '%s:%s\n' "${FORTRESS_BASIC_AUTH_USER}" "${hash}" >"${FORTRESS_HTPASSWD_FILE}"
  elif [ ! -s "${FORTRESS_HTPASSWD_FILE}" ]; then
    echo "No Basic Auth password supplied and no existing htpasswd file found." >&2
    exit 1
  fi

  if getent group www-data >/dev/null 2>&1; then
    chgrp www-data "${FORTRESS_HTPASSWD_FILE}" || true
    chmod 640 "${FORTRESS_HTPASSWD_FILE}"
  else
    chmod 644 "${FORTRESS_HTPASSWD_FILE}"
  fi
}

ensure_self_signed_cert() {
  local cert_dir="/etc/ssl/fortress"
  local cert_file="${cert_dir}/${FORTRESS_REMOTE_HOSTNAME}.crt"
  local key_file="${cert_dir}/${FORTRESS_REMOTE_HOSTNAME}.key"

  install -d "${cert_dir}"
  if [ ! -f "${cert_file}" ] || [ ! -f "${key_file}" ]; then
    openssl req -x509 -nodes -newkey rsa:2048 -days 30 \
      -keyout "${key_file}" \
      -out "${cert_file}" \
      -subj "/CN=${FORTRESS_REMOTE_HOSTNAME}" >/dev/null 2>&1
    chmod 600 "${key_file}"
    chmod 644 "${cert_file}"
  fi

  printf '%s\n%s\n' "${cert_file}" "${key_file}"
}

cert_paths_for_host() {
  local host="$1"
  local fallback_cert="$2"
  local fallback_key="$3"
  local le_dir="/etc/letsencrypt/live/${host}"

  if [ -f "${le_dir}/fullchain.pem" ] && [ -f "${le_dir}/privkey.pem" ]; then
    printf '%s\n%s\n' "${le_dir}/fullchain.pem" "${le_dir}/privkey.pem"
  else
    printf '%s\n%s\n' "${fallback_cert}" "${fallback_key}"
  fi
}

write_nginx_site() {
  local host="$1"
  local site_name="$2"
  local cert_file="$3"
  local key_file="$4"
  local target="/etc/nginx/sites-available/${site_name}"
  local link="/etc/nginx/sites-enabled/${site_name}"

  cat >"${target}" <<NGINX
server {
    listen 80;
    server_name ${host};

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
    server_name ${host};

    ssl_certificate ${cert_file};
    ssl_certificate_key ${key_file};

    auth_basic "Fortress Phronesis";
    auth_basic_user_file ${FORTRESS_HTPASSWD_FILE};

    add_header Cache-Control "no-store";

    location / {
        proxy_pass http://127.0.0.1:${FORTRESS_WATCH_PORT};
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
    }
}
NGINX

  ln -sfn "${target}" "${link}"
}

remove_legacy_temp_site() {
  rm -f "/etc/nginx/sites-enabled/${FORTRESS_LEGACY_TEMP_HOSTNAME}"
  rm -f "/etc/nginx/sites-available/${FORTRESS_LEGACY_TEMP_HOSTNAME}"
}

maybe_issue_cert() {
  local host="$1"
  local email_mode="$2"

  if ! command -v certbot >/dev/null 2>&1; then
    return 0
  fi

  if [ -f "/etc/letsencrypt/live/${host}/fullchain.pem" ] && [ -f "/etc/letsencrypt/live/${host}/privkey.pem" ]; then
    return 0
  fi

  resolved_ip="$(getent ahostsv4 "${host}" | awk '{print $1; exit}' || true)"
  if [ -z "${resolved_ip:-}" ] || [ "${resolved_ip}" != "${FORTRESS_PUBLIC_IP}" ]; then
    log "Skipping certbot for ${host}; DNS resolves to '${resolved_ip:-none}', expected ${FORTRESS_PUBLIC_IP}."
    return 0
  fi

  if [ "${email_mode}" = "email" ]; then
    certbot certonly --webroot -w "${ACME_WEBROOT}" -d "${host}" \
      --non-interactive --agree-tos --email "${FORTRESS_CERTBOT_EMAIL}" --keep-until-expiring
  else
    certbot certonly --webroot -w "${ACME_WEBROOT}" -d "${host}" \
      --non-interactive --agree-tos --register-unsafely-without-email --keep-until-expiring
  fi
}

log "Validating Fortress source root"
require_file "${FORTRESS_DEPLOY_ROOT}/compose.yaml"
require_file "${FORTRESS_DEPLOY_ROOT}/.env.contabo.example"
touch "${FORTRESS_DEPLOY_ROOT}/.fortress-personal-deploy-root"

if [ ! -f "${FORTRESS_ENV_FILE}" ]; then
  log "Creating ${FORTRESS_ENV_FILE}"
  write_default_env
fi

log "Deploying Docker Compose project ${FORTRESS_COMPOSE_PROJECT}"
cd "${FORTRESS_DEPLOY_ROOT}"
docker compose -p "${FORTRESS_COMPOSE_PROJECT}" --env-file "${FORTRESS_ENV_FILE}" -f compose.yaml config --quiet
docker compose -p "${FORTRESS_COMPOSE_PROJECT}" --env-file "${FORTRESS_ENV_FILE}" -f compose.yaml up -d --build

log "Configuring Basic Auth"
ensure_basic_auth

log "Installing Nginx routes"
install -d /etc/nginx/sites-available /etc/nginx/sites-enabled "${ACME_WEBROOT}"
mapfile -t fallback_paths < <(ensure_self_signed_cert)
fallback_cert="${fallback_paths[0]}"
fallback_key="${fallback_paths[1]}"

mapfile -t permanent_paths < <(cert_paths_for_host "${FORTRESS_REMOTE_HOSTNAME}" "${fallback_cert}" "${fallback_key}")
write_nginx_site "${FORTRESS_REMOTE_HOSTNAME}" "${FORTRESS_REMOTE_HOSTNAME}" "${permanent_paths[0]}" "${permanent_paths[1]}"
remove_legacy_temp_site

nginx -t
systemctl reload nginx || nginx -s reload

maybe_issue_cert "${FORTRESS_REMOTE_HOSTNAME}" "email"

mapfile -t permanent_paths < <(cert_paths_for_host "${FORTRESS_REMOTE_HOSTNAME}" "${fallback_cert}" "${fallback_key}")
write_nginx_site "${FORTRESS_REMOTE_HOSTNAME}" "${FORTRESS_REMOTE_HOSTNAME}" "${permanent_paths[0]}" "${permanent_paths[1]}"
remove_legacy_temp_site

nginx -t
systemctl reload nginx || nginx -s reload

log "Running local smokes"
curl -fsS "http://127.0.0.1:${FORTRESS_API_PORT}/healthz"
curl -fsSI "http://127.0.0.1:${FORTRESS_WATCH_PORT}/" >/dev/null
curl -fsS "http://127.0.0.1:${FORTRESS_WATCH_PORT}/api/healthz"

remote_status="$(curl -kIs --resolve "${FORTRESS_REMOTE_HOSTNAME}:443:127.0.0.1" "https://${FORTRESS_REMOTE_HOSTNAME}/" | awk 'NR==1 {print $2}')"
if [ "${remote_status}" != "401" ] && [ -z "${FORTRESS_BASIC_AUTH_PASSWORD:-}" ]; then
  printf 'Expected unauthenticated %s route to return 401, got %s\n' "${FORTRESS_REMOTE_HOSTNAME}" "${remote_status}" >&2
  exit 1
fi

if [ -n "${FORTRESS_BASIC_AUTH_PASSWORD:-}" ]; then
  curl -kfsS --resolve "${FORTRESS_REMOTE_HOSTNAME}:443:127.0.0.1" \
    -u "${FORTRESS_BASIC_AUTH_USER}:${FORTRESS_BASIC_AUTH_PASSWORD}" \
    "https://${FORTRESS_REMOTE_HOSTNAME}/api/healthz" >/dev/null
fi

docker compose -p "${FORTRESS_COMPOSE_PROJECT}" --env-file "${FORTRESS_ENV_FILE}" -f compose.yaml ps
log "Fortress personal deployment complete"
