#!/usr/bin/env bash
# Pull wp-config.php from a remote WordPress instance to ./data/wp-config.php.backup
# Requires SSH_HOST and WP_PATH env vars.

set -euo pipefail

if [ -z "${SSH_HOST:-}" ] || [ -z "${WP_PATH:-}" ]; then
  echo "Set SSH_HOST (user@host) and WP_PATH (remote WP directory) before running." >&2
  exit 1
fi

DEST="/Users/benjaminlagrone/Documents/projects/askmortgageauthority.com/data"
mkdir -p "${DEST}"

echo "==> Pulling wp-config.php from ${SSH_HOST}:${WP_PATH}"
scp "${SSH_HOST}:${WP_PATH}/wp-config.php" "${DEST}/wp-config.php.backup"

echo "Saved to ${DEST}/wp-config.php.backup"
