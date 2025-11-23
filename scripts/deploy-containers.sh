#!/usr/bin/env bash
# Bootstrap script to bring up PericopeAI (frontend + API) and AMA Chat containers
# on new host ports, connect them to the shared Docker network, and print Nginx
# upstream hints for cutover. This does not edit Nginx or stop host processes.

set -euo pipefail

NETWORK="pericope_net"
COMPOSE_FILE="docker-compose.pericope.yml"
KEYCLOAK_CONTAINER="auth-keycloak-1"
KEYCLOAK_DB_CONTAINER="kc-db"

# Host ports to map container services onto
API_HOST_PORT=18000     # PericopeAI API
FE_HOST_PORT=13080      # PericopeAI frontend
CHAT_HOST_PORT=19001    # AMA Chat API (once added to compose)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${REPO_ROOT}"

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || { echo "Missing required command: $1" >&2; exit 1; }
}

require_cmd docker

echo "==> Ensuring network ${NETWORK} exists"
if ! docker network ls --format '{{.Name}}' | grep -q "^${NETWORK}$"; then
  docker network create "${NETWORK}"
fi

connect_if_present() {
  local container="$1"
  if docker ps -a --format '{{.Names}}' | grep -q "^${container}$"; then
    if ! docker network inspect "${NETWORK}" | grep -q "\"Name\": \"${container}\""; then
      docker network connect "${NETWORK}" "${container}"
    fi
  fi
}

echo "==> Connecting Keycloak containers to ${NETWORK} if present"
connect_if_present "${KEYCLOAK_CONTAINER}"
connect_if_present "${KEYCLOAK_DB_CONTAINER}"

echo "==> Bringing up compose stack (${COMPOSE_FILE})"
if [ ! -f "${COMPOSE_FILE}" ]; then
  echo "Compose file ${COMPOSE_FILE} not found in ${REPO_ROOT}. Create it before running." >&2
  exit 1
fi

docker compose -f "${COMPOSE_FILE}" up -d

echo "==> Done. Verify containers are running:"
echo "    docker compose -f ${COMPOSE_FILE} ps"

cat <<EOF

Next steps:
1) Update host Nginx upstreams to the mapped ports:
   upstream pericope_api { server 127.0.0.1:${API_HOST_PORT}; }
   upstream pericope_fe  { server 127.0.0.1:${FE_HOST_PORT}; }
   upstream ama_chat     { server 127.0.0.1:${CHAT_HOST_PORT}; }  # when chat container added

2) Routes:
   pericopeai.com:
     location /api { proxy_pass http://pericope_api; ... }
     location /    { proxy_pass http://pericope_fe; ... }
   chat.askmortgageauthority.com (or /chat):
     proxy_pass http://ama_chat;

3) Reload Nginx after edits: nginx -t && nginx -s reload

4) Stop old host uvicorn processes once traffic is flowing through containers.
EOF
