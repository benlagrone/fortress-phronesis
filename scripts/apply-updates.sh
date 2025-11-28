#!/usr/bin/env bash
# Pull latest code for PericopeAI (backend + frontend) and redeploy containers.
# Assumes:
# - fortress-phronesis repo at /root/workspace/fortress-phronesis (this script location)
# - Backend repo at /root/workspace/AugustineService
# - Frontend repo at /root/workspace/AugustineFE
# - docker-compose.pericope.yml present in fortress-phronesis repo root

set -euo pipefail

FPR_ROOT="/root/workspace/fortress-phronesis"
API_REPO="/root/workspace/AugustineService"
FE_REPO="/root/workspace/AugustineFE"
COMPOSE_FILE="docker-compose.pericope.yml"

cd "${FPR_ROOT}"

echo "==> Pulling fortress-phronesis"
git pull --ff-only || true

echo "==> Pulling backend (AugustineService)"
git -C "${API_REPO}" pull --ff-only || true

echo "==> Pulling frontend (AugustineFE)"
git -C "${FE_REPO}" pull --ff-only || true

echo "==> Building updated containers"
docker compose -f "${COMPOSE_FILE}" build pericopeai-api pericopeai-frontend

echo "==> Deploying updated containers"
docker compose -f "${COMPOSE_FILE}" up -d pericopeai-api pericopeai-frontend

echo "==> Done. Verify:"
echo "   curl -I http://127.0.0.1:18000/api/docs"
echo "   curl -I http://127.0.0.1:13080"
echo "   curl -I https://pericopeai.com/api/docs"
echo "If nginx was modified, reload: nginx -t && nginx -s reload"
