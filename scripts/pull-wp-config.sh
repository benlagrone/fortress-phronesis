#!/usr/bin/env bash
# Pull wp-config.php from a remote WordPress instance to ./data/wp-config.php.backup
# Requires SSH_HOST and WP_PATH env vars.

set -euo pipefail

# Load required env file alongside this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${SCRIPT_DIR}/.env"
if [ ! -f "${ENV_FILE}" ]; then
  echo "Missing ${ENV_FILE}. Create it with SSH_HOST, WP_PATH (and optional USER)." >&2
  exit 1
fi
set -o allexport
source "${ENV_FILE}"
set +o allexport

# Require SSH_HOST and WP_PATH after sourcing
if [ -z "${SSH_HOST:-}" ] || [ -z "${WP_PATH:-}" ]; then
  echo "SSH_HOST and WP_PATH must be set in ${ENV_FILE}." >&2
  exit 1
fi

# If SSH_HOST is just a host/IP and USER is set, prefix it
if [[ "${SSH_HOST}" != *"@"* ]] && [ -n "${USER:-}" ]; then
  SSH_HOST="${USER}@${SSH_HOST}"
fi

# If SSH_HOST is just a host/IP and USER is set, prefix it
if [[ "${SSH_HOST}" != *"@"* ]] && [ -n "${USER:-}" ]; then
  SSH_HOST="${USER}@${SSH_HOST}"
fi

REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
DEST="${REPO_ROOT}/data"
mkdir -p "${DEST}"

echo "==> Pulling wp-config.php from ${SSH_HOST}:${WP_PATH}"
if [ -n "${PW:-}" ]; then
  SSHPASS="${PW}" sshpass -e scp "${SSH_HOST}:${WP_PATH}/wp-config.php" "${DEST}/wp-config.php.backup"
else
  scp "${SSH_HOST}:${WP_PATH}/wp-config.php" "${DEST}/wp-config.php.backup"
fi

echo "Saved to ${DEST}/wp-config.php.backup"
