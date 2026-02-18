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

compose_pericope() {
  COMPOSE_IGNORE_ORPHANS=1 docker compose -p "${COMPOSE_PROJECT}" -f "${COMPOSE_FILE}" "$@"
}

wait_for_http_ok() {
  local label="$1"
  local url="$2"
  local attempts="${3:-20}"
  local sleep_seconds="${4:-2}"
  local i
  for ((i=1; i<=attempts; i++)); do
    if curl -fsS "${url}" >/dev/null 2>&1; then
      echo "==> ${label} is ready (${url})"
      return 0
    fi
    sleep "${sleep_seconds}"
  done
  echo "ERROR: ${label} did not become ready after ${attempts} attempts: ${url}" >&2
  return 1
}

bootstrap_db_with_retry() {
  local mysql_attempts="${MYSQL_READY_ATTEMPTS:-30}"
  local mysql_sleep_seconds="${MYSQL_READY_SLEEP_SECONDS:-2}"
  local attempts="${DB_BOOTSTRAP_ATTEMPTS:-20}"
  local sleep_seconds="${DB_BOOTSTRAP_SLEEP_SECONDS:-3}"
  local ready=0
  local i

  for ((i=1; i<=mysql_attempts; i++)); do
    if compose_pericope exec -T mysql sh -lc 'mysqladmin ping -h 127.0.0.1 -uroot -p"$MYSQL_ROOT_PASSWORD" --silent' >/dev/null 2>&1; then
      ready=1
      echo "==> MySQL is ready"
      break
    fi
    sleep "${mysql_sleep_seconds}"
  done

  if [[ "${ready}" -ne 1 ]]; then
    echo "ERROR: MySQL did not become ready after ${mysql_attempts} attempts" >&2
    return 1
  fi

  for ((i=1; i<=attempts; i++)); do
    local output
    output="$(compose_pericope exec -T pericopeai-api python create_tables.py 2>&1 || true)"
    echo "${output}"
    if grep -q "Database setup completed successfully!" <<<"${output}"; then
      echo "==> DB bootstrap succeeded"
      return 0
    fi
    echo "==> DB bootstrap not ready yet (${i}/${attempts}); retrying in ${sleep_seconds}s"
    sleep "${sleep_seconds}"
  done

  echo "ERROR: DB bootstrap failed after ${attempts} attempts" >&2
  return 1
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FPR_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
WORKSPACE_ROOT="${WORKSPACE_ROOT:-$(cd "${FPR_ROOT}/.." && pwd)}"

API_REPO="${API_REPO:-${WORKSPACE_ROOT}/AugustineService}"
FE_REPO="${FE_REPO:-${WORKSPACE_ROOT}/AugustineFE}"
CORPUS_REPO="${CORPUS_REPO:-${WORKSPACE_ROOT}/AugustineCorpus}"

if [[ -n "${GATEWAY_REPO_DIR:-}" ]]; then
  GATEWAY_REPO_DIR="${GATEWAY_REPO_DIR}"
elif [[ -d "${WORKSPACE_ROOT}/CorpusGateway" ]]; then
  GATEWAY_REPO_DIR="${WORKSPACE_ROOT}/CorpusGateway"
elif [[ -d "${WORKSPACE_ROOT}/AugustineCorpusGateway" ]]; then
  GATEWAY_REPO_DIR="${WORKSPACE_ROOT}/AugustineCorpusGateway"
else
  GATEWAY_REPO_DIR="${WORKSPACE_ROOT}/CorpusGateway"
fi

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
compose_pericope up -d --build \
  augustine-corpus-live pericopeai-api pericopeai-frontend

echo "==> Applying DB bootstrap in API container"
bootstrap_db_with_retry

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
compose_pericope ps
wait_for_http_ok "API" "http://127.0.0.1:18000/api/healthz"
wait_for_http_ok "Frontend" "http://127.0.0.1:13080"
if [[ "${GATEWAY_ENABLED}" -eq 1 ]]; then
  wait_for_http_ok "Gateway" "http://127.0.0.1:18002/healthz"
fi

echo "==> Done."
