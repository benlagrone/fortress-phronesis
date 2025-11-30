#!/usr/bin/env bash
# Pull wp-content from a remote WordPress instance to ./data/wp-content
# Requires SSH_HOST and WP_PATH env vars.

set -euo pipefail

SSH_HOST="${SSH_HOST:-root@vmi2669159}"
WP_PATH="${WP_PATH:-/var/www/askmortgageauthority}"

DEST="/Users/benjaminlagrone/Documents/projects/askmortgageauthority.com/data/wp-content"
mkdir -p "${DEST}"

echo "==> Syncing wp-content from ${SSH_HOST}:${WP_PATH}/wp-content/ to ${DEST}/"
rsync -avz --delete "${SSH_HOST}:${WP_PATH}/wp-content/" "${DEST}/"

echo "Done. Local copy in ${DEST}"
