#!/usr/bin/env bash
set -euo pipefail

log() {
  printf '[backup] %s\n' "$*" >&2
}

first_existing() {
  local path
  for path in "$@"; do
    if [ -e "$path" ]; then
      printf '%s\n' "$path"
      return 0
    fi
  done
  return 1
}

extract_define() {
  local key="$1"
  sed -nE "s/.*define\([[:space:]]*['\"]${key}['\"][[:space:]]*,[[:space:]]*['\"]([^'\"]*)['\"].*/\1/p" "$WP_CONFIG" | head -n1
}

BACKUP_ROOT="${BACKUP_ROOT_INPUT:-${HOME}/backups/ama-wordpress}"
mkdir -p "$BACKUP_ROOT"

WP_PATH="$(first_existing /var/www/askmortgageauthority /var/www/askmortgageauthority.com || true)"
if [ -z "${WP_PATH:-}" ]; then
  WP_CONFIG="$(find /var/www /srv /home -maxdepth 4 -type f -name 'wp-config.php' 2>/dev/null | head -n1)"
  [ -n "${WP_CONFIG:-}" ] || {
    log 'Unable to find wp-config.php'
    exit 1
  }
  WP_PATH="$(dirname "$WP_CONFIG")"
fi

WP_CONFIG="${WP_PATH}/wp-config.php"
[ -f "$WP_CONFIG" ] || {
  log "Missing ${WP_CONFIG}"
  exit 1
}
[ -d "${WP_PATH}/wp-content" ] || {
  log "Missing ${WP_PATH}/wp-content"
  exit 1
}

DB_NAME="$(extract_define DB_NAME)"
DB_USER="$(extract_define DB_USER)"
DB_PASSWORD="$(extract_define DB_PASSWORD)"
DB_HOST_RAW="$(extract_define DB_HOST)"
[ -n "$DB_HOST_RAW" ] || DB_HOST_RAW="localhost"

[ -n "$DB_NAME" ] || {
  log 'DB_NAME missing'
  exit 1
}
[ -n "$DB_USER" ] || {
  log 'DB_USER missing'
  exit 1
}

DB_HOST="$DB_HOST_RAW"
DB_PORT="3306"
DB_SOCKET=""
if [[ "$DB_HOST_RAW" == *:* ]]; then
  host_part="${DB_HOST_RAW%%:*}"
  suffix="${DB_HOST_RAW#*:}"
  if [[ "$suffix" == /* ]]; then
    DB_HOST="$host_part"
    DB_SOCKET="$suffix"
  elif [[ "$suffix" =~ ^[0-9]+$ ]]; then
    DB_HOST="$host_part"
    DB_PORT="$suffix"
  fi
fi

DUMP_BIN="$(command -v mysqldump || command -v mariadb-dump || true)"
[ -n "$DUMP_BIN" ] || {
  log 'mysqldump/mariadb-dump not found'
  exit 1
}

RELEASE_ID="$(date -u +%Y%m%dT%H%M%SZ)"
RELEASE_DIR="${BACKUP_ROOT}/${RELEASE_ID}"
mkdir -p "${RELEASE_DIR}/nginx"

log "Backing up wp-config from ${WP_CONFIG}"
cp "$WP_CONFIG" "${RELEASE_DIR}/wp-config.php.backup"

log "Backing up wp-content from ${WP_PATH}/wp-content"
tar -C "$WP_PATH" -czf "${RELEASE_DIR}/live-wp-content.tar.gz" wp-content

log "Backing up database ${DB_NAME}"
dump_args=(--single-transaction --routines --triggers --events -u "$DB_USER")
if [ -n "$DB_SOCKET" ]; then
  dump_args+=(--socket="$DB_SOCKET")
elif [ -n "$DB_HOST" ]; then
  dump_args+=(-h "$DB_HOST" -P "$DB_PORT")
fi
MYSQL_PWD="$DB_PASSWORD" "$DUMP_BIN" "${dump_args[@]}" "$DB_NAME" | gzip -c > "${RELEASE_DIR}/live-db.sql.gz"

log 'Snapshotting nginx config'
cp -a /etc/nginx/sites-available/*askmortgageauthority* "${RELEASE_DIR}/nginx/" 2>/dev/null || true
cp -a /etc/nginx/sites-enabled/*askmortgageauthority* "${RELEASE_DIR}/nginx/" 2>/dev/null || true

if command -v sha256sum >/dev/null 2>&1; then
  wp_sha="$(sha256sum "${RELEASE_DIR}/live-wp-content.tar.gz" | awk '{print $1}')"
  db_sha="$(sha256sum "${RELEASE_DIR}/live-db.sql.gz" | awk '{print $1}')"
else
  wp_sha=""
  db_sha=""
fi

wp_size="$(wc -c < "${RELEASE_DIR}/live-wp-content.tar.gz" | tr -d ' ')"
db_size="$(wc -c < "${RELEASE_DIR}/live-db.sql.gz" | tr -d ' ')"

{
  printf 'release_id=%s\n' "$RELEASE_ID"
  printf 'release_dir=%s\n' "$RELEASE_DIR"
  printf 'wp_path=%s\n' "$WP_PATH"
  printf 'wp_config=%s\n' "$WP_CONFIG"
  printf 'db_name=%s\n' "$DB_NAME"
  printf 'db_host_raw=%s\n' "$DB_HOST_RAW"
  printf 'db_backup=%s\n' "${RELEASE_DIR}/live-db.sql.gz"
  printf 'db_backup_bytes=%s\n' "$db_size"
  printf 'db_backup_sha256=%s\n' "$db_sha"
  printf 'wp_content_backup=%s\n' "${RELEASE_DIR}/live-wp-content.tar.gz"
  printf 'wp_content_backup_bytes=%s\n' "$wp_size"
  printf 'wp_content_backup_sha256=%s\n' "$wp_sha"
  printf 'created_at=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
} > "${RELEASE_DIR}/manifest.env"

printf 'release_id=%s\n' "$RELEASE_ID"
printf 'release_dir=%s\n' "$RELEASE_DIR"
printf 'wp_path=%s\n' "$WP_PATH"
printf 'db_name=%s\n' "$DB_NAME"
printf 'db_backup=%s\n' "${RELEASE_DIR}/live-db.sql.gz"
printf 'wp_content_backup=%s\n' "${RELEASE_DIR}/live-wp-content.tar.gz"
printf 'manifest=%s\n' "${RELEASE_DIR}/manifest.env"
