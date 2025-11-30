#!/usr/bin/env bash
# Pull wp-config.php from a remote WordPress instance to ./data/wp-config.php.backup
# Requires SSH_HOST and WP_PATH env vars.

set -euo pipefail

SSH_HOST="${SSH_HOST:-root@vmi2669159}"
WP_PATH="${WP_PATH:-/var/www/askmortgageauthority}"

DEST="/Users/benjaminlagrone/Documents/projects/askmortgageauthority.com/data"
mkdir -p "${DEST}"

echo "==> Pulling wp-config.php from ${SSH_HOST}:${WP_PATH}"
scp "${SSH_HOST}:${WP_PATH}/wp-config.php" "${DEST}/wp-config.php.backup"

echo "Saved to ${DEST}/wp-config.php.backup"
