#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="$ROOT_DIR/docker-compose.pericope.yml"
CORPUS_ENV_FILE="$ROOT_DIR/../AugustineCorpus/.env"
SERVICE_ENV_FILE="$ROOT_DIR/../AugustineService/.env"
FE_ENV_FILE="$ROOT_DIR/../AugustineFE/.env"

if [[ ! -f "$COMPOSE_FILE" ]]; then
  echo "FAIL: compose file not found: $COMPOSE_FILE"
  exit 1
fi

failures=0

pass() {
  echo "PASS: $1"
}

fail() {
  echo "FAIL: $1"
  failures=$((failures + 1))
}

require_pattern() {
  local pattern="$1"
  local label="$2"
  if grep -n -F "$pattern" "$COMPOSE_FILE" >/dev/null; then
    pass "$label"
  else
    fail "$label (missing pattern: $pattern)"
  fi
}

forbid_pattern() {
  local pattern="$1"
  local label="$2"
  if grep -n -E "$pattern" "$COMPOSE_FILE" >/dev/null; then
    fail "$label (forbidden pattern found: $pattern)"
  else
    pass "$label"
  fi
}

echo "Verifying immutable PericopeAI deployment contract..."
echo "Compose file: $COMPOSE_FILE"

require_pattern "name: fortress-phronesis-net" "Network name is locked"
require_pattern "\"3307:3306\"" "MySQL host port is locked to 3307"
require_pattern "\"18000:8080\"" "API host port is locked to 18000"
require_pattern "\"13080:80\"" "Frontend host port is locked to 13080"
require_pattern "\"8086:8080\"" "Solomonic Clock host port is locked to 8086"
require_pattern "ENVIRONMENT=\${ENVIRONMENT:-dev}" "Corpus ENVIRONMENT wiring is locked"
require_pattern "ENV=\${ENV:-dev}" "Corpus ENV wiring is locked"
require_pattern "CORPUS_API_URL=\${CORPUS_API_URL:-http://augustine-corpus-live:8001}" "API corpus URL wiring is locked"
require_pattern "SOLOMONIC_PERICOPE_API_BASE=\${SOLOMONIC_PERICOPE_API_BASE:-http://augustine-corpus-live:8001}" "Clock corpus wiring is locked"
require_pattern "REACT_APP_ENVIRONMENT: \${REACT_APP_ENVIRONMENT:-dev}" "Frontend build environment wiring is locked"
require_pattern "SOLOMONIC_CLOCK_UPSTREAM=\${SOLOMONIC_CLOCK_UPSTREAM:-http://solomonic-clock:8080}" "Frontend clock upstream wiring is locked"

forbid_pattern "\\$\\{PERICOPE_NET_NAME" "Network override is disabled"
forbid_pattern "\\$\\{MYSQL_HOST_PORT" "MySQL port override is disabled"
forbid_pattern "\\$\\{API_HOST_PORT" "API port override is disabled"
forbid_pattern "\\$\\{FE_HOST_PORT" "Frontend port override is disabled"
forbid_pattern "\\$\\{SOLOMONIC_HOST_PORT" "Solomonic Clock port override is disabled"
forbid_pattern "host\\.docker\\.internal:8086" "Frontend no longer defaults to host clock port"

env_value() {
  local key="$1"
  local file="$2"
  if [[ -f "$file" ]]; then
    awk -F= -v key="$key" '$1 == key {sub(/^[^=]*=/, ""); print; exit}' "$file"
  fi
}

if [[ -f "$CORPUS_ENV_FILE" ]]; then
  corpus_provider="$(env_value MODEL_PROVIDER "$CORPUS_ENV_FILE")"
  if [[ -z "$corpus_provider" ]]; then
    corpus_provider="$(env_value LLM_PROVIDER "$CORPUS_ENV_FILE")"
  fi
  corpus_provider="$(printf '%s' "$corpus_provider" | tr '[:upper:]' '[:lower:]')"

  if [[ "$corpus_provider" == "ollama" ]]; then
    ollama_url="$(env_value OLLAMA_BASE_URL "$CORPUS_ENV_FILE")"
    if [[ -z "$ollama_url" ]]; then
      ollama_url="$(env_value OLLAMA_URL "$CORPUS_ENV_FILE")"
    fi
    allow_private_ollama="$(env_value ALLOW_PRIVATE_OLLAMA_URL "$CORPUS_ENV_FILE")"
    allow_private_ollama="$(printf '%s' "$allow_private_ollama" | tr '[:upper:]' '[:lower:]')"

    if [[ -z "$ollama_url" ]]; then
      fail "Corpus MODEL_PROVIDER=ollama requires OLLAMA_BASE_URL or OLLAMA_URL in AugustineCorpus/.env"
    elif [[ "$ollama_url" =~ ^https?://192\.168\.0\.126:11434/?$ ]]; then
      pass "Corpus Ollama URL uses the documented Fortress IPsec endpoint"
    elif [[ "$allow_private_ollama" != "true" ]] && [[ "$ollama_url" =~ ^https?://(localhost|127\.|0\.0\.0\.0|host\.docker\.internal) ]]; then
      fail "Corpus Ollama URL must not point at local-only container/host addresses ($ollama_url); use the documented Fortress IPsec endpoint or set ALLOW_PRIVATE_OLLAMA_URL=true only for intentional non-prod use"
    else
      pass "Corpus Ollama provider has an explicit non-local URL or private-url override"
    fi
  fi
fi

# In production, frontend API key must be present in FE env because it is a build-time arg.
if [[ -f "$SERVICE_ENV_FILE" && -f "$FE_ENV_FILE" ]]; then
  if grep -Eq '^(ENV|ENVIRONMENT)=prd$' "$SERVICE_ENV_FILE"; then
    if grep -Eq '^REACT_APP_AUGUSTINE_API_KEY=.+$' "$FE_ENV_FILE"; then
      pass "Prod FE API key is present in AugustineFE/.env"
    else
      fail "Prod FE API key missing/empty in AugustineFE/.env (REACT_APP_AUGUSTINE_API_KEY)"
    fi
  fi
fi

if [[ "$failures" -gt 0 ]]; then
  echo
  echo "Deployment lock check FAILED with $failures issue(s)."
  exit 1
fi

echo
echo "Deployment lock check PASSED."
