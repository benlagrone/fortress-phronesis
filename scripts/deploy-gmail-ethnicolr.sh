#!/usr/bin/env bash
set -euo pipefail

CLIENT_SECRET_JSON_B64="$(printf '%s' "${CLIENT_SECRET_JSON}" | base64 -w 0)"

ssh -i ~/.ssh/id_ed25519 "${DEPLOY_USER}@${DEPLOY_HOST}"   "APP_REPO='${APP_REPO}' APP_IMAGE='${APP_IMAGE}' GOOGLE_EXPECTED_EMAIL='${GOOGLE_EXPECTED_EMAIL}' REPO_PULL_TOKEN='${REPO_PULL_TOKEN}' GHCR_READ_TOKEN='${GHCR_READ_TOKEN}' CLIENT_SECRET_JSON_B64='${CLIENT_SECRET_JSON_B64}' TOKEN_PKL_B64='${TOKEN_PKL_B64}' bash -s" <<'REMOTE'
set -euo pipefail

APP_ROOT="${HOME}/workspace/gmail_ethnicolr_tagger"
REPO_URL="https://x-access-token:${REPO_PULL_TOKEN}@github.com/${APP_REPO}.git"

run_root() {
  if [ "$(id -u)" -eq 0 ]; then
    "$@"
  else
    sudo "$@"
  fi
}

install -d "$(dirname "${APP_ROOT}")"

if [ ! -d "${APP_ROOT}/.git" ]; then
  git clone "${REPO_URL}" "${APP_ROOT}"
fi

git -C "${APP_ROOT}" remote set-url origin "${REPO_URL}"
git -C "${APP_ROOT}" fetch origin main
git -C "${APP_ROOT}" checkout main
git -C "${APP_ROOT}" pull --ff-only origin main

if [ -n "${GHCR_READ_TOKEN:-}" ]; then
  printf '%s' "${GHCR_READ_TOKEN}" | docker login ghcr.io -u benlagrone --password-stdin
fi

cd "${APP_ROOT}"
install -d secrets data

cat > .env <<EOF
APP_IMAGE=ghcr.io/benlagrone/gmail_ethnicolr_tagger
IMAGE_TAG=latest
API_BIND_HOST=127.0.0.1
API_PORT=5001
SECRETS_DIR=../secrets
DATA_DIR=../data
GOOGLE_OAUTH_USE_CONSOLE=1
GOOGLE_EXPECTED_EMAIL=${GOOGLE_EXPECTED_EMAIL}
EOF

printf '%s' "${CLIENT_SECRET_JSON_B64}" | base64 -d > secrets/client_secret.json

if [ -n "${TOKEN_PKL_B64:-}" ]; then
  printf '%s' "${TOKEN_PKL_B64}" | base64 -d > data/token.pkl
fi

docker compose --env-file .env -f deploy/docker-compose.prod.yml pull ethnicolr-api
docker compose --env-file .env -f deploy/docker-compose.prod.yml up -d ethnicolr-api

run_root cp deploy/systemd/gmail-ethnicolr-api.service /etc/systemd/system/
run_root cp deploy/systemd/gmail-ethnicolr-bot.service /etc/systemd/system/
run_root cp deploy/systemd/gmail-ethnicolr-bot.timer /etc/systemd/system/
run_root systemctl daemon-reload
run_root systemctl enable --now gmail-ethnicolr-api.service

if [ -s data/token.pkl ]; then
  run_root systemctl enable --now gmail-ethnicolr-bot.timer
else
  run_root systemctl disable --now gmail-ethnicolr-bot.timer || true
  echo "Token file missing; bot timer left disabled."
fi

run_root systemctl status gmail-ethnicolr-api.service --no-pager
run_root systemctl status gmail-ethnicolr-bot.timer --no-pager || true
curl -fsS http://127.0.0.1:5001/ >/dev/null
REMOTE
