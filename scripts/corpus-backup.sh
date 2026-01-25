#!/usr/bin/env bash
set -euo pipefail

# Utility script to pack/restore corpus texts and Docker index volumes.

CONTROL_PLANE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

DEFAULT_TEXTS_PATH="/root/workspace/AugustineCorpus/texts"
ALT_TEXTS_PATH="/Users/benjaminlagrone/Documents/projects/pericopeai.com/AugustineCorpus/texts"
TEXTS_PATH="${TEXTS_PATH:-$DEFAULT_TEXTS_PATH}"

if [[ ! -d "$TEXTS_PATH" && -d "$ALT_TEXTS_PATH" ]]; then
  TEXTS_PATH="$ALT_TEXTS_PATH"
fi

BACKUP_DIR="${BACKUP_DIR:-$CONTROL_PLANE_ROOT/backups}"
mkdir -p "$BACKUP_DIR"

timestamp() {
  date +"%Y%m%d-%H%M%S"
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "Missing required command: $1" >&2
    exit 1
  }
}

checksum_file() {
  local file="$1"
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$file" > "${file}.sha256"
  else
    require_cmd shasum
    shasum -a 256 "$file" > "${file}.sha256"
  fi
  echo "Checksum written: ${file}.sha256"
}

pack_texts() {
  if [[ ! -d "$TEXTS_PATH" ]]; then
    echo "Texts path not found: $TEXTS_PATH" >&2
    echo "Override with TEXTS_PATH=/path/to/AugustineCorpus/texts" >&2
    exit 1
  fi
  local archive="${1:-corpus-texts-$(timestamp).tgz}"
  local parent
  parent="$(dirname "$TEXTS_PATH")"
  local base
  base="$(basename "$TEXTS_PATH")"
  local dest="$BACKUP_DIR/$archive"

  echo "Packing texts: $TEXTS_PATH -> $dest"
  tar -czf "$dest" -C "$parent" "$base"
  checksum_file "$dest"
}

pack_volume() {
  require_cmd docker
  local volume="$1"
  local archive="${2:-${volume}-$(timestamp).tgz}"
  local dest="$BACKUP_DIR/$archive"

  echo "Packing volume: $volume -> $dest"
  docker run --rm \
    -v "${volume}:/data" \
    -v "${BACKUP_DIR}:/backup" \
    alpine sh -c "tar -czf /backup/${archive} -C /data ."
  checksum_file "$dest"
}

restore_volume() {
  require_cmd docker
  local volume="$1"
  local archive_path="$2"
  local archive_dir
  archive_dir="$(cd "$(dirname "$archive_path")" && pwd)"
  local archive_file
  archive_file="$(basename "$archive_path")"

  if [[ ! -f "$archive_dir/$archive_file" ]]; then
    echo "Archive not found: $archive_dir/$archive_file" >&2
    exit 1
  fi

  echo "Restoring volume: $volume <- $archive_dir/$archive_file"
  docker run --rm \
    -v "${volume}:/data" \
    -v "${archive_dir}:/backup" \
    alpine sh -c "tar -xzf /backup/${archive_file} -C /data"
}

pack_all_index_volumes() {
  require_cmd docker
  require_cmd rg
  local volumes
  volumes="$(docker volume ls --format '{{.Name}}' | rg '^corpus_.*_index$' || true)"
  if [[ -z "$volumes" ]]; then
    echo "No corpus index volumes found (pattern: corpus_*_index)." >&2
    exit 1
  fi
  while IFS= read -r vol; do
    [[ -z "$vol" ]] && continue
    pack_volume "$vol"
  done <<< "$volumes"
}

usage() {
  cat <<EOF
Usage:
  $(basename "$0") pack-texts [archive-name.tgz]
  $(basename "$0") pack-volume <docker-volume> [archive-name.tgz]
  $(basename "$0") restore-volume <docker-volume> </path/to/archive.tgz>
  $(basename "$0") pack-all-index-volumes

Environment overrides:
  TEXTS_PATH=/path/to/AugustineCorpus/texts
  BACKUP_DIR=/path/to/backups
EOF
}

main() {
  local cmd="${1:-}"
  case "$cmd" in
    pack-texts)
      pack_texts "${2:-}"
      ;;
    pack-volume)
      [[ $# -lt 2 ]] && usage && exit 1
      pack_volume "$2" "${3:-}"
      ;;
    restore-volume)
      [[ $# -lt 3 ]] && usage && exit 1
      restore_volume "$2" "$3"
      ;;
    pack-all-index-volumes)
      pack_all_index_volumes
      ;;
    *)
      usage
      exit 1
      ;;
  esac
}

main "$@"

