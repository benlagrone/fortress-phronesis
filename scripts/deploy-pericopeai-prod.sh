#!/usr/bin/env bash
set -euo pipefail

# Control-plane helper to deploy pericopeai.com (AugustineService) on prod.
# Steps: down, git pull, start DB, rebuild API, run migrations, health check.

APP_PATH=${APP_PATH:-/root/workspace/AugustineService}
COMPOSE_FILE=${COMPOSE_FILE:-docker-compose.yml}
API_SERVICE=${API_SERVICE:-api}
DB_SERVICE=${DB_SERVICE:-mysql}
HEALTH_URL=${HEALTH_URL:-http://localhost:8080/api/healthz}
CREATE_TABLES_CMD=${CREATE_TABLES_CMD:-python create_tables.py}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || { echo "Missing required command: $1" >&2; exit 1; }
}

require_cmd git
require_cmd docker
require_cmd curl

if [[ ! -d "$APP_PATH" ]]; then
  # Fallback to the macOS path if the server path is absent
  ALT_PATH="/Users/benjaminlagrone/Documents/projects/pericopeai.com/AugustineService"
  if [[ -d "$ALT_PATH" ]]; then
    APP_PATH="$ALT_PATH"
  else
    echo "App path not found: $APP_PATH" >&2
    echo "Override with APP_PATH=/path/to/AugustineService when running the script." >&2
    exit 1
  fi
fi

cd "$APP_PATH"

if [[ ! -f "$COMPOSE_FILE" ]]; then
  echo "Compose file not found: $COMPOSE_FILE (cwd: $APP_PATH)" >&2
  exit 1
fi

echo "==> Pulling latest code in $APP_PATH"
git pull --ff-only

echo "==> Stopping existing stack"
docker compose -f "$COMPOSE_FILE" down

echo "==> Starting database ($DB_SERVICE)"
docker compose -f "$COMPOSE_FILE" up -d "$DB_SERVICE"

echo "==> Rebuilding and starting API ($API_SERVICE)"
docker compose -f "$COMPOSE_FILE" up -d --build "$API_SERVICE"

echo "==> Applying DB migrations via $API_SERVICE: $CREATE_TABLES_CMD"
docker compose -f "$COMPOSE_FILE" exec "$API_SERVICE" $CREATE_TABLES_CMD

echo "==> Health check $HEALTH_URL"
curl -i "$HEALTH_URL"

cat <<'EOF'

Optional DB sanity check (uses env-provided creds):
  docker compose -f '"$COMPOSE_FILE"' exec '"$DB_SERVICE"' mysql -u"${MYSQL_USER:-augustine}" -p"${MYSQL_PASS:-password}" "${MYSQL_DB:-augustine_chat}" -e "show tables;"

Note: Uses server-specific .env in the app directory; do not overwrite prod secrets.
EOF
