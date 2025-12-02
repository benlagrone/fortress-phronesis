#!/usr/bin/env bash
# Build and deploy PericopeAI (API + FE) plus the corpus service.
# Assumes:
# - Control repo: /root/workspace/fortress-phronesis
# - AugustineCorpus repo: /root/workspace/AugustineCorpus
# - External network: pericope_net
# Optional: set RUN_INDEX=1 to run the indexer profile after corpus is up.

set -euo pipefail

FPR_ROOT="/root/workspace/fortress-phronesis"
CORPUS_ROOT="/root/workspace/AugustineCorpus"
PERICOPE_COMPOSE="${FPR_ROOT}/docker-compose.pericope.yml"
CORPUS_COMPOSE="${CORPUS_ROOT}/docker-compose.corpus.yml"

echo "==> Ensuring network pericope_net exists"
docker network create pericope_net 2>/dev/null || true

echo "==> Deploying corpus service (augustine-corpus-1-0-0)"
docker compose -f "${CORPUS_COMPOSE}" up -d --build augustine-corpus-1-0-0

if [ "${RUN_INDEX:-0}" = "1" ]; then
  echo "==> Running indexer profile (one-shot)"
  docker compose -f "${CORPUS_COMPOSE}" --profile index run --rm pericopeai-indexer || true
fi

echo "==> Deploying PericopeAI API + Frontend"
docker compose -f "${PERICOPE_COMPOSE}" up -d --build pericopeai-api pericopeai-frontend

echo "==> Done. Verify:"
echo "  curl -I http://127.0.0.1:8001/healthz        # corpus"
echo "  curl -I http://127.0.0.1:18000/api/docs      # API"
echo "  curl -I http://127.0.0.1:13080               # FE"
