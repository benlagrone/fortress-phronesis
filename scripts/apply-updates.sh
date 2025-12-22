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
CORPUS_REPO="/root/workspace/AugustineCorpus"
GATEWAY_REPO="/root/workspace/CorpusGateway"
COMPOSE_FILE="docker-compose.pericope.yml"
GATEWAY_COMPOSE_FILE="docker-compose.gateway.yml"

cd "${FPR_ROOT}"

echo "==> Pulling fortress-phronesis"
git pull --ff-only || true

echo "==> Pulling backend (AugustineService)"
git -C "${API_REPO}" pull --ff-only || true

echo "==> Pulling frontend (AugustineFE)"
git -C "${FE_REPO}" pull --ff-only || true

echo "==> Pulling corpus (AugustineCorpus)"
git -C "${CORPUS_REPO}" pull --ff-only || true

echo "==> Pulling gateway (CorpusGateway)"
git -C "${GATEWAY_REPO}" pull --ff-only || true

echo "==> Building updated containers"
docker compose -f "${COMPOSE_FILE}" build augustine-corpus-live pericopeai-api pericopeai-frontend

echo "==> Deploying updated containers"
docker compose -f "${COMPOSE_FILE}" up -d augustine-corpus-live pericopeai-api pericopeai-frontend

echo "==> Deploying corpus gateway"
docker compose -f "${GATEWAY_COMPOSE_FILE}" up -d --build corpus-gateway

echo "==> Done. Verify:"
echo "   curl -I http://127.0.0.1:18000/api/docs"
echo "   curl -I http://127.0.0.1:13080"
echo "   curl -I http://127.0.0.1:18002/healthz"
echo "   curl -I https://pericopeai.com/api/docs"
echo "If nginx was modified, reload: nginx -t && nginx -s reload"
