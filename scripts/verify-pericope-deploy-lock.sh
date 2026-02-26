#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="$ROOT_DIR/docker-compose.pericope.yml"

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
require_pattern "\"3000:80\"" "Frontend host port is locked to 3000"
require_pattern "ENVIRONMENT=\${ENVIRONMENT:-dev}" "Corpus ENVIRONMENT wiring is locked"
require_pattern "ENV=\${ENV:-dev}" "Corpus ENV wiring is locked"
require_pattern "CORPUS_API_URL=\${CORPUS_API_URL:-http://augustine-corpus-live:8001}" "API corpus URL wiring is locked"
require_pattern "REACT_APP_ENVIRONMENT: \${REACT_APP_ENVIRONMENT:-dev}" "Frontend build environment wiring is locked"

forbid_pattern "\\$\\{PERICOPE_NET_NAME" "Network override is disabled"
forbid_pattern "\\$\\{MYSQL_HOST_PORT" "MySQL port override is disabled"
forbid_pattern "\\$\\{API_HOST_PORT" "API port override is disabled"
forbid_pattern "\\$\\{FE_HOST_PORT" "Frontend port override is disabled"

if [[ "$failures" -gt 0 ]]; then
  echo
  echo "Deployment lock check FAILED with $failures issue(s)."
  exit 1
fi

echo
echo "Deployment lock check PASSED."
