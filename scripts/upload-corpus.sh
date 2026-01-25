#!/usr/bin/env bash
set -euo pipefail

# Pack and upload corpus artifacts (texts and/or index volumes) to a remote host.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKUP_DIR="${BACKUP_DIR:-$ROOT_DIR/backups}"
BACKUP_SCRIPT="$ROOT_DIR/scripts/corpus-backup.sh"

HOST=""
DEST=""
PACK_TEXTS=1
PACK_VOLUMES=0
FILE=""

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "Missing required command: $1" >&2
    exit 1
  }
}

usage() {
  cat <<EOF
Usage:
  $(basename "$0") --host user@host --dest /remote/path [options]

Options:
  --no-pack-texts       Do not pack texts before upload
  --pack-volumes        Pack all corpus_*_index volumes before upload
  --file /path/to.tgz   Upload a specific archive (and its .sha256 if present)

Environment:
  BACKUP_DIR=/path/to/backups
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --host)
      HOST="${2:-}"
      shift 2
      ;;
    --dest)
      DEST="${2:-}"
      shift 2
      ;;
    --no-pack-texts)
      PACK_TEXTS=0
      shift
      ;;
    --pack-volumes)
      PACK_VOLUMES=1
      shift
      ;;
    --file)
      FILE="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage
      exit 1
      ;;
  esac
done

if [[ -z "$HOST" || -z "$DEST" ]]; then
  usage
  exit 1
fi

require_cmd rsync
require_cmd "$BACKUP_SCRIPT"

mkdir -p "$BACKUP_DIR"

if [[ "$PACK_TEXTS" -eq 1 ]]; then
  "$BACKUP_SCRIPT" pack-texts
fi

if [[ "$PACK_VOLUMES" -eq 1 ]]; then
  "$BACKUP_SCRIPT" pack-all-index-volumes
fi

files_to_upload=()

if [[ -n "$FILE" ]]; then
  files_to_upload+=("$FILE")
  [[ -f "${FILE}.sha256" ]] && files_to_upload+=("${FILE}.sha256")
else
  latest_texts="$(ls -t "$BACKUP_DIR"/corpus-texts-*.tgz 2>/dev/null | head -n 1 || true)"
  if [[ -n "$latest_texts" ]]; then
    files_to_upload+=("$latest_texts")
    [[ -f "${latest_texts}.sha256" ]] && files_to_upload+=("${latest_texts}.sha256")
  fi
  if [[ "$PACK_VOLUMES" -eq 1 ]]; then
    while IFS= read -r vol_archive; do
      [[ -z "$vol_archive" ]] && continue
      files_to_upload+=("$vol_archive")
      [[ -f "${vol_archive}.sha256" ]] && files_to_upload+=("${vol_archive}.sha256")
    done < <(ls -t "$BACKUP_DIR"/corpus_*_index-*.tgz 2>/dev/null || true)
  fi
fi

if [[ "${#files_to_upload[@]}" -eq 0 ]]; then
  echo "No archives found to upload in $BACKUP_DIR" >&2
  exit 1
fi

echo "Uploading ${#files_to_upload[@]} file(s) to $HOST:$DEST"
rsync -avP "${files_to_upload[@]}" "$HOST:$DEST/"

echo "Upload complete."

