#!/usr/bin/env bash
# Pull wp-content from a remote WordPress instance to ./data/wp-content
# Requires SSH_HOST and WP_PATH env vars.

set -euo pipefail

if [ -z "${SSH_HOST:-}" ] || [ -z "${WP_PATH:-}" ]; then
  echo "Set SSH_HOST (user@host) and WP_PATH (remote WP directory) before running." >&2
  exit 1
fi

mkdir -p ./data/wp-content

echo "==> Syncing wp-content from ${SSH_HOST}:${WP_PATH}/wp-content/ to ./data/wp-content/"
rsync -avz --delete "${SSH_HOST}:${WP_PATH}/wp-content/" "./data/wp-content/"

echo "Done. Local copy in ./data/wp-content"
