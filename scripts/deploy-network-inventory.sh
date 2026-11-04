#!/bin/bash
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/.." && pwd)
cd "$ROOT"
bash scripts/verify-network-inventory-lock.sh
if [ -n "$(git status --porcelain -- services/network-inventory scripts/deploy-network-inventory.sh docker-compose.network-inventory.yml scripts/verify-network-inventory-lock.sh)" ]; then
  echo 'Commit the reviewed DNA release before deployment.' >&2; exit 1
fi
revision=$(git rev-parse HEAD)
ssh_args=(-o BatchMode=yes -o ConnectTimeout=10 -o StrictHostKeyChecking=yes -o HostKeyAlias=fortress-sextant.lan 100.121.75.0)
remote="Library/Application Support/Fortress/dna/releases/$revision"
# Fixed host, fixed managed root, commit-addressed artifact. No unrelated files are transferred.
ssh "${ssh_args[@]}" "umask 077; mkdir -p \"\$HOME/$remote\""
git archive "$revision" services/network-inventory docker-compose.network-inventory.yml | ssh "${ssh_args[@]}" "tar -xf - -C \"\$HOME/$remote\""
ssh "${ssh_args[@]}" "/usr/local/bin/python3.12 \"\$HOME/$remote/services/network-inventory/deploy/install.py\" \"\$HOME/$remote\" '$revision'"
