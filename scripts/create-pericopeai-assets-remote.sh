#!/usr/bin/env bash
# Create the pericopeai-assets GitHub repo if needed, wire origin, and push main.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FORTRESS_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
ASSETS_ROOT="${ASSETS_ROOT:-${FORTRESS_ROOT}/../pericopeai-assets}"
OWNER="${GITHUB_OWNER:-benlagrone}"
REPO="${GITHUB_REPO:-pericopeai-assets}"
DESCRIPTION="${GITHUB_REPO_DESCRIPTION:-Shared static assets for PericopeAI and True Vine OS}"
PRIVATE="${GITHUB_REPO_PRIVATE:-false}"
OWNER_TYPE="${GITHUB_OWNER_TYPE:-user}"
REMOTE_URL="https://github.com/${OWNER}/${REPO}.git"

if [ ! -d "${ASSETS_ROOT}/.git" ]; then
  echo "Expected a git repo at ${ASSETS_ROOT}" >&2
  exit 1
fi

if command -v gh >/dev/null 2>&1; then
  if ! gh repo view "${OWNER}/${REPO}" >/dev/null 2>&1; then
    VISIBILITY_FLAG='--public'
    if [ "${PRIVATE}" = 'true' ]; then
      VISIBILITY_FLAG='--private'
    fi
    gh repo create "${OWNER}/${REPO}" "${VISIBILITY_FLAG}" --description "${DESCRIPTION}" >/dev/null
  fi
else
  TOKEN="${GITHUB_TOKEN:-${GH_TOKEN:-}}"
  if [ -z "${TOKEN}" ]; then
    echo 'gh is not installed and GITHUB_TOKEN/GH_TOKEN is not set.' >&2
    exit 1
  fi

  API='https://api.github.com'
  AUTH=(-H "Accept: application/vnd.github+json" -H "Authorization: Bearer ${TOKEN}" -H "X-GitHub-Api-Version: 2022-11-28")
  STATUS="$(curl -sS -o /dev/null -w '%{http_code}' "${AUTH[@]}" "${API}/repos/${OWNER}/${REPO}")"

  if [ "${STATUS}" = '404' ]; then
    CREATE_URL="${API}/user/repos"
    if [ "${OWNER_TYPE}" = 'org' ]; then
      CREATE_URL="${API}/orgs/${OWNER}/repos"
    fi
    curl -fsS -X POST "${AUTH[@]}" "${CREATE_URL}"           -d "{"name":"${REPO}","private":${PRIVATE},"description":"${DESCRIPTION}"}" >/dev/null
  elif [ "${STATUS}" != '200' ]; then
    echo "GitHub API returned HTTP ${STATUS} while checking ${OWNER}/${REPO}" >&2
    exit 1
  fi
fi

if git -C "${ASSETS_ROOT}" remote get-url origin >/dev/null 2>&1; then
  git -C "${ASSETS_ROOT}" remote set-url origin "${REMOTE_URL}"
else
  git -C "${ASSETS_ROOT}" remote add origin "${REMOTE_URL}"
fi

git -C "${ASSETS_ROOT}" push -u origin main
echo "Pushed ${ASSETS_ROOT} to ${REMOTE_URL}"
