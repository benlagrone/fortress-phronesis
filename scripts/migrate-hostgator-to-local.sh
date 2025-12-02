#!/usr/bin/env bash
set -euo pipefail

# Seed the local MySQL container (control-plane compose mysql service)
# with schema/data from HostGator.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || { echo "Missing required command: $1" >&2; exit 1; }
}

require_cmd docker
require_cmd mysqldump

# Allow overriding the API env file location; default to the API repo env.
API_ENV_FILE=${API_ENV_FILE:-/root/workspace/AugustineService/.env}
if [[ -f "${API_ENV_FILE}" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "${API_ENV_FILE}"
  set +a
fi

# HostGator source creds (fallback to API env MYSQL_* if present).
HOSTGATOR_HOST=${HOSTGATOR_HOST:-${MYSQL_HOST:-}}
HOSTGATOR_USER=${HOSTGATOR_USER:-${MYSQL_USER:-}}
HOSTGATOR_PASS=${HOSTGATOR_PASS:-${MYSQL_PASS:-}}
HOSTGATOR_DB=${HOSTGATOR_DB:-${MYSQL_DB:-}}

# Local target: defaults to this repo's compose mysql service (not HostGator creds).
LOCAL_COMPOSE_FILE=${LOCAL_COMPOSE_FILE:-"${REPO_ROOT}/docker-compose.pericope.yml"}
LOCAL_MYSQL_SERVICE=${LOCAL_MYSQL_SERVICE:-mysql}
LOCAL_DEFAULT_DB=${LOCAL_DEFAULT_DB:-augustine_chat}
LOCAL_DEFAULT_USER=${LOCAL_DEFAULT_USER:-augustine}
LOCAL_DEFAULT_PASS=${LOCAL_DEFAULT_PASS:-password}
LOCAL_DB=${LOCAL_DB:-${LOCAL_MYSQL_DB:-${LOCAL_DEFAULT_DB}}}
LOCAL_USER=${LOCAL_USER:-${LOCAL_MYSQL_USER:-${LOCAL_DEFAULT_USER}}}
LOCAL_PASS=${LOCAL_PASS:-${LOCAL_MYSQL_PASS:-${LOCAL_DEFAULT_PASS}}}
DUMP_OPTS=${DUMP_OPTS:---no-tablespaces}
DUMP_FILE=${DUMP_FILE:-/tmp/hostgator_dump.sql}

if [[ -z "$HOSTGATOR_HOST" || -z "$HOSTGATOR_USER" || -z "$HOSTGATOR_PASS" || -z "$HOSTGATOR_DB" ]]; then
  echo "Set HOSTGATOR_HOST, HOSTGATOR_USER, HOSTGATOR_PASS, HOSTGATOR_DB env vars before running." >&2
  exit 1
fi
if [[ -z "$LOCAL_DB" || -z "$LOCAL_USER" || -z "$LOCAL_PASS" ]]; then
  echo "Set LOCAL_DB, LOCAL_USER, LOCAL_PASS (or MYSQL_DB/USER/PASS) before running." >&2
  exit 1
fi
if [[ ! -f "$LOCAL_COMPOSE_FILE" ]]; then
  echo "Compose file not found: $LOCAL_COMPOSE_FILE" >&2
  exit 1
fi

echo "==> Dumping HostGator DB $HOSTGATOR_DB from $HOSTGATOR_HOST..."
mysqldump $DUMP_OPTS -h "$HOSTGATOR_HOST" -u "$HOSTGATOR_USER" -p"$HOSTGATOR_PASS" "$HOSTGATOR_DB" > "$DUMP_FILE"
echo "==> Dump complete: $DUMP_FILE"

echo "==> Copying dump into local MySQL container..."
LOCAL_MYSQL_CID=$(docker compose -f "$LOCAL_COMPOSE_FILE" ps -q "$LOCAL_MYSQL_SERVICE")
if [[ -z "$LOCAL_MYSQL_CID" ]]; then
  echo "Local MySQL service ($LOCAL_MYSQL_SERVICE) not running for compose file $LOCAL_COMPOSE_FILE" >&2
  exit 1
fi
docker cp "$DUMP_FILE" "$LOCAL_MYSQL_CID":/tmp/hostgator_dump.sql

echo "==> Importing into local DB $LOCAL_DB..."
docker compose -f "$LOCAL_COMPOSE_FILE" exec "$LOCAL_MYSQL_SERVICE" sh -c \
  "mysql -u\"$LOCAL_USER\" --password=\"${LOCAL_PASS}\" \"$LOCAL_DB\" < /tmp/hostgator_dump.sql"

echo "==> Migration complete."
