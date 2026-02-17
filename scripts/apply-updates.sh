#!/usr/bin/env bash
# Pull latest code for PericopeAI and redeploy containers with the same contract
# across dev/prod: shared network + same compose project default.

set -euo pipefail

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "Missing required command: $1" >&2
    exit 1
  }
}

require_repo() {
  local label="$1"
  local path="$2"
  if [[ ! -d "${path}/.git" ]]; then
    echo "Missing git repo for ${label}: ${path}" >&2
    exit 1
  fi
}

pull_repo() {
  local label="$1"
  local path="$2"
  echo "==> Pulling ${label}"
  git -C "${path}" pull --ff-only || true
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FPR_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
WORKSPACE_ROOT="${WORKSPACE_ROOT:-$(cd "${FPR_ROOT}/.." && pwd)}"

API_REPO="${API_REPO:-${WORKSPACE_ROOT}/AugustineService}"
FE_REPO="${FE_REPO:-${WORKSPACE_ROOT}/AugustineFE}"
CORPUS_REPO="${CORPUS_REPO:-${WORKSPACE_ROOT}/AugustineCorpus}"
GATEWAY_REPO_DIR="${GATEWAY_REPO_DIR:-${WORKSPACE_ROOT}/CorpusGateway}"
GATEWAY_REPO_NAME="${GATEWAY_REPO_NAME:-$(basename "${GATEWAY_REPO_DIR}")}"

COMPOSE_FILE="${COMPOSE_FILE:-${FPR_ROOT}/docker-compose.pericope.yml}"
GATEWAY_COMPOSE_FILE="${GATEWAY_COMPOSE_FILE:-${FPR_ROOT}/docker-compose.gateway.yml}"
COMPOSE_PROJECT="${COMPOSE_PROJECT:-fortress-phronesis}"
PERICOPE_NET_NAME="${PERICOPE_NET_NAME:-fortress-phronesis-net}"

require_cmd git
require_cmd docker
require_cmd curl

require_repo "fortress-phronesis" "${FPR_ROOT}"
require_repo "AugustineService" "${API_REPO}"
require_repo "AugustineFE" "${FE_REPO}"
require_repo "AugustineCorpus" "${CORPUS_REPO}"

echo "==> Workspace root: ${WORKSPACE_ROOT}"
echo "==> Compose project: ${COMPOSE_PROJECT}"
echo "==> Shared network: ${PERICOPE_NET_NAME}"

cd "${FPR_ROOT}"

echo "==> Ensuring shared network exists"
docker network create "${PERICOPE_NET_NAME}" >/dev/null 2>&1 || true

pull_repo "fortress-phronesis" "${FPR_ROOT}"
pull_repo "AugustineService" "${API_REPO}"
pull_repo "AugustineFE" "${FE_REPO}"
pull_repo "AugustineCorpus" "${CORPUS_REPO}"

if [[ -d "${GATEWAY_REPO_DIR}/.git" ]]; then
  pull_repo "CorpusGateway" "${GATEWAY_REPO_DIR}"
else
  echo "==> Skipping CorpusGateway pull (repo not found at ${GATEWAY_REPO_DIR})"
fi

echo "==> Deploying core containers"
docker compose -p "${COMPOSE_PROJECT}" -f "${COMPOSE_FILE}" up -d --build \
  augustine-corpus-live pericopeai-api pericopeai-frontend

echo "==> Applying DB bootstrap in API container"
docker compose -p "${COMPOSE_PROJECT}" -f "${COMPOSE_FILE}" exec -T pericopeai-api \
  python create_tables.py

GATEWAY_ENABLED=0
if [[ -f "${GATEWAY_COMPOSE_FILE}" && -d "${GATEWAY_REPO_DIR}" ]]; then
  echo "==> Deploying corpus gateway"
  WORKSPACE_ROOT="${WORKSPACE_ROOT}" \
  GATEWAY_REPO="${GATEWAY_REPO_NAME}" \
  PERICOPE_NET_NAME="${PERICOPE_NET_NAME}" \
  docker compose -p "${COMPOSE_PROJECT}" -f "${GATEWAY_COMPOSE_FILE}" up -d --build corpus-gateway
  GATEWAY_ENABLED=1
else
  echo "==> Skipping gateway deploy (compose file or repo missing)"
fi

echo "==> Verifying services"
docker compose -p "${COMPOSE_PROJECT}" -f "${COMPOSE_FILE}" ps
curl -fsS http://127.0.0.1:18000/api/healthz && echo
curl -fsSI http://127.0.0.1:13080 >/dev/null
if [[ "${GATEWAY_ENABLED}" -eq 1 ]]; then
  curl -fsS http://127.0.0.1:18002/healthz && echo
fi

echo "==> Done."
