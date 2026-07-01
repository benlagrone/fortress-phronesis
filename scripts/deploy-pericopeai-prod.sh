#!/usr/bin/env bash
set -euo pipefail

# Control-plane helper to deploy the PericopeAI API on the locked
# fortress-phronesis compose stack. It intentionally does not run the legacy
# standalone AugustineService compose project.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORKSPACE_ROOT=${WORKSPACE_ROOT:-"$(dirname "$ROOT_DIR")"}
APP_PATH=${APP_PATH:-"$WORKSPACE_ROOT/AugustineService"}
APP_REPO_URL=${APP_REPO_URL:-git@github.com:benlagrone/AugustineService.git}
APP_REF=${APP_REF:-master}
SOURCE_SHA=${SOURCE_SHA:-}
COMPOSE_PROJECT=${COMPOSE_PROJECT:-fortress-phronesis}
COMPOSE_FILE=${COMPOSE_FILE:-"$ROOT_DIR/docker-compose.pericope.yml"}
API_SERVICE=${API_SERVICE:-pericopeai-api}
HEALTH_URL=${HEALTH_URL:-http://127.0.0.1:18000/api/healthz}
AUTHORS_URL=${AUTHORS_URL:-http://127.0.0.1:18000/api/v1/authors}
PUBLIC_HOST=${PUBLIC_HOST:-pericopeai.com}
PUBLIC_RESOLVE_IP=${PUBLIC_RESOLVE_IP:-127.0.0.1}
PUBLIC_HEALTH_URL=${PUBLIC_HEALTH_URL:-https://${PUBLIC_HOST}/api/healthz}
CREATE_TABLES_CMD=${CREATE_TABLES_CMD:-python create_tables.py}
SYNC_AUTHOR_CATALOG_CMD=${SYNC_AUTHOR_CATALOG_CMD:-python sync_author_catalog.py --corpus-base http://augustine-corpus-live:8001 --exclude-local-only}
SKIP_GIT_SYNC=${SKIP_GIT_SYNC:-false}
SKIP_MIGRATIONS=${SKIP_MIGRATIONS:-false}
SKIP_AUTHOR_SYNC=${SKIP_AUTHOR_SYNC:-false}
SKIP_PUBLIC_SMOKE=${SKIP_PUBLIC_SMOKE:-false}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || { echo "Missing required command: $1" >&2; exit 1; }
}

require_cmd git
require_cmd docker
require_cmd curl

if [[ ! -f "$COMPOSE_FILE" ]]; then
  echo "Compose file not found: $COMPOSE_FILE" >&2
  exit 1
fi

if [[ ! -d "$APP_PATH/.git" ]]; then
  echo "App checkout not found: $APP_PATH" >&2
  echo "Override APP_PATH or clone AugustineService beside fortress-phronesis." >&2
  exit 1
fi

compose() {
  docker compose -p "$COMPOSE_PROJECT" -f "$COMPOSE_FILE" "$@"
}

retry_curl() {
  local url="$1"
  shift
  local attempt
  for attempt in $(seq 1 30); do
    if curl -fsS --max-time 15 "$@" "$url" >/dev/null; then
      return 0
    fi
    sleep 2
  done
  curl -fsS --max-time 15 "$@" "$url" >/dev/null
}

sync_app_checkout() {
  echo "==> Syncing AugustineService checkout: $APP_PATH"
  git -C "$APP_PATH" remote set-url origin "$APP_REPO_URL"
  git -C "$APP_PATH" fetch origin "$APP_REF"
  git -C "$APP_PATH" checkout "$APP_REF"

  local local_head
  local remote_head
  local_head="$(git -C "$APP_PATH" rev-parse HEAD)"
  remote_head="$(git -C "$APP_PATH" rev-parse "origin/$APP_REF")"

  if [[ "$local_head" == "$remote_head" ]]; then
    echo "AugustineService already matches origin/$APP_REF @ $local_head"
  elif git -C "$APP_PATH" merge-base --is-ancestor "$local_head" "$remote_head"; then
    git -C "$APP_PATH" merge --ff-only "origin/$APP_REF"
  elif git -C "$APP_PATH" merge-base --is-ancestor "$remote_head" "$local_head"; then
    echo "AugustineService is ahead of origin/$APP_REF; deploying local HEAD $local_head"
  else
    echo "AugustineService has diverged from origin/$APP_REF; merge before deploying." >&2
    git -C "$APP_PATH" status --short --branch >&2 || true
    exit 1
  fi

  if [[ -n "$SOURCE_SHA" ]]; then
    git -C "$APP_PATH" fetch origin "$SOURCE_SHA" || true
    git -C "$APP_PATH" checkout "$SOURCE_SHA"
  fi
}

cd "$ROOT_DIR"

echo "==> Verifying PericopeAI deployment lock"
bash scripts/verify-pericope-deploy-lock.sh

if [[ "$SKIP_GIT_SYNC" != "true" ]]; then
  sync_app_checkout
else
  echo "==> Skipping AugustineService git sync; deploying current checkout"
fi

echo "==> Rebuilding and starting $API_SERVICE via locked Fortress compose"
compose up -d --build "$API_SERVICE"

if [[ "$SKIP_MIGRATIONS" != "true" ]]; then
  echo "==> Applying DB migrations via $API_SERVICE: $CREATE_TABLES_CMD"
  compose exec -T "$API_SERVICE" $CREATE_TABLES_CMD
fi

if [[ "$SKIP_AUTHOR_SYNC" != "true" ]]; then
  echo "==> Syncing author catalog via $API_SERVICE: $SYNC_AUTHOR_CATALOG_CMD"
  compose exec -T "$API_SERVICE" $SYNC_AUTHOR_CATALOG_CMD
fi

echo "==> Compose status"
compose ps "$API_SERVICE"

echo "==> Health check $HEALTH_URL"
retry_curl "$HEALTH_URL"

echo "==> Authors check $AUTHORS_URL"
retry_curl "$AUTHORS_URL"

if [[ "$SKIP_PUBLIC_SMOKE" != "true" ]]; then
  echo "==> Public host health check $PUBLIC_HEALTH_URL via $PUBLIC_RESOLVE_IP"
  retry_curl "$PUBLIC_HEALTH_URL" --resolve "${PUBLIC_HOST}:443:${PUBLIC_RESOLVE_IP}"
fi

cat <<'EOF'

Deployment complete. Follow-up checks:
  docker compose -p fortress-phronesis -f docker-compose.pericope.yml logs --tail=200 pericopeai-api
  curl -fsS http://127.0.0.1:18000/api/healthz
  curl -fsS --resolve pericopeai.com:443:127.0.0.1 https://pericopeai.com/api/healthz

Note: Uses server-specific .env in the app directory; do not overwrite prod secrets.
EOF
