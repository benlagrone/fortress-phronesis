#!/usr/bin/env bash
# Build and (re)deploy the calculators site container.
# Assumptions:
# - Calculators repo is cloned at /root/workspace/ama-calculators (update CALC_REPO if different)
# - Dockerfile in that repo is as provided (serves FastAPI on :8000 inside container)
# - Host port 18010 is free and used for mapping (change HOST_PORT if needed)
# - Container name calculators-app (change CONTAINER if desired)

set -euo pipefail

CALC_REPO="/root/workspace/ama-calculators"  # TODO: update to your calculators repo path
COMPOSE_FILE="${CALC_REPO}/docker-compose.yml"
IMAGE_NAME="ama-calculators"
CONTAINER="calculators-app"
HOST_PORT=18010
CONTAINER_PORT=8000

if [ -f "${COMPOSE_FILE}" ]; then
  echo "==> Using compose at ${COMPOSE_FILE}"
  docker compose -f "${COMPOSE_FILE}" build
  docker compose -f "${COMPOSE_FILE}" up -d
else
  echo "==> No compose file found, building image ${IMAGE_NAME} from ${CALC_REPO}"
  docker build -t "${IMAGE_NAME}" "${CALC_REPO}"
  echo "==> Stopping/removing existing container (if any)"
  docker rm -f "${CONTAINER}" 2>/dev/null || true
  echo "==> Running container ${CONTAINER} on host port ${HOST_PORT}"
  docker run -d \
    --name "${CONTAINER}" \
    -p "${HOST_PORT}:${CONTAINER_PORT}" \
    --restart unless-stopped \
    "${IMAGE_NAME}"
fi

echo "==> Done. Verify:"
echo "   curl -I http://127.0.0.1:${HOST_PORT}"
echo "Then point nginx for calculators.askmortgageauthority.com to http://127.0.0.1:${HOST_PORT}"
echo "Note: healthcheck uses curl inside the container; ensure curl is installed in the image."
