#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  sync-prod-repo.sh --check-clean <repo_path> [repo_label]
  sync-prod-repo.sh <repo_path> <repo_url> <repo_ref> [repo_label] [clone_if_missing|require_existing]

This helper keeps a production-side git checkout exactly aligned to the remote
branch before a deploy runs. It fails if the worktree is dirty, if the local
branch has drifted from origin, or if the requested repo cannot be prepared.
EOF
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "Missing required command: $1" >&2
    exit 1
  }
}

print_repo_status() {
  local repo_path="$1"
  git -C "$repo_path" status --short --branch --untracked-files=all || true
}

filtered_repo_status() {
  local repo_path="$1"
  local line
  local path
  local allowed_path

  # Allow root-level server-local env files that are intentionally untracked on the host.
  while IFS= read -r line; do
    case "$line" in
      "?? .env"*.local)
        continue
        ;;
    esac

    if [[ "$line" == "?? "* ]]; then
      path="${line:3}"
      while IFS= read -r allowed_path; do
        [[ -n "${allowed_path}" ]] || continue
        case "$path" in
          "${allowed_path}"|"${allowed_path}"/*)
            continue 2
            ;;
        esac
      done <<< "${SYNC_PROD_ALLOWED_DIRTY_PATHS:-}"
    fi

    printf '%s\n' "$line"
  done < <(git -C "$repo_path" status --porcelain --untracked-files=all || true)
}

fail_repo() {
  local message="$1"
  local repo_path="$2"
  echo "FAIL: ${message}" >&2
  if [[ -d "${repo_path}/.git" ]]; then
    print_repo_status "$repo_path" >&2
  fi
  exit 1
}

require_clean_repo() {
  local repo_path="$1"
  local repo_label="$2"
  local phase="$3"

  if [[ -n "$(filtered_repo_status "$repo_path")" ]]; then
    fail_repo "${repo_label} is dirty ${phase}" "$repo_path"
  fi
}

require_cmd git

if [[ "${1:-}" == "--check-clean" ]]; then
  if [[ $# -lt 2 ]]; then
    usage >&2
    exit 1
  fi

  REPO_PATH="$2"
  REPO_LABEL="${3:-$REPO_PATH}"

  if [[ ! -d "${REPO_PATH}/.git" ]]; then
    echo "FAIL: ${REPO_LABEL} checkout is missing at ${REPO_PATH}" >&2
    exit 1
  fi

  require_clean_repo "${REPO_PATH}" "${REPO_LABEL}" "during deploy"
  echo "PASS: ${REPO_LABEL} remained clean"
  exit 0
fi

if [[ $# -lt 3 ]]; then
  usage >&2
  exit 1
fi

REPO_PATH="$1"
REPO_URL="$2"
REPO_REF="$3"
REPO_LABEL="${4:-$REPO_PATH}"
CLONE_POLICY="${5:-clone_if_missing}"

case "$CLONE_POLICY" in
  clone_if_missing|require_existing)
    ;;
  *)
    echo "Unknown clone policy: ${CLONE_POLICY}" >&2
    usage >&2
    exit 1
    ;;
esac

if [[ ! -d "${REPO_PATH}/.git" ]]; then
  if [[ "$CLONE_POLICY" == "require_existing" ]]; then
    echo "FAIL: ${REPO_LABEL} checkout is missing at ${REPO_PATH}" >&2
    exit 1
  fi

  install -d "$(dirname "${REPO_PATH}")"
  git clone "${REPO_URL}" "${REPO_PATH}"
fi

git -C "${REPO_PATH}" remote set-url origin "${REPO_URL}"

require_clean_repo "${REPO_PATH}" "${REPO_LABEL}" "before sync"

git -C "${REPO_PATH}" fetch origin --tags

if ! git -C "${REPO_PATH}" show-ref --verify --quiet "refs/remotes/origin/${REPO_REF}"; then
  fail_repo "${REPO_LABEL} is missing origin/${REPO_REF}" "${REPO_PATH}"
fi

if git -C "${REPO_PATH}" show-ref --verify --quiet "refs/heads/${REPO_REF}"; then
  git -C "${REPO_PATH}" checkout "${REPO_REF}"
else
  git -C "${REPO_PATH}" checkout -B "${REPO_REF}" --track "origin/${REPO_REF}"
fi

git -C "${REPO_PATH}" merge --ff-only "origin/${REPO_REF}"

local_head="$(git -C "${REPO_PATH}" rev-parse HEAD)"
remote_head="$(git -C "${REPO_PATH}" rev-parse "origin/${REPO_REF}")"
if [[ "${local_head}" != "${remote_head}" ]]; then
  fail_repo "${REPO_LABEL} is not exactly aligned to origin/${REPO_REF}" "${REPO_PATH}"
fi

require_clean_repo "${REPO_PATH}" "${REPO_LABEL}" "after sync"

echo "PASS: ${REPO_LABEL} synced to ${REPO_REF} @ ${local_head}"
