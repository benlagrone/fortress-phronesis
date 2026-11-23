#!/usr/bin/env bash
# Read-only smoke checks for the Sextant remote edge.
# SEXTANT_STATUS_TOKEN is read from the environment and is never printed.
# Do not pass the token as an argument. Do not run this script under set -x.

set -euo pipefail
umask 077

BASE_URL="https://sextant.lecrowndevelopment.com"
ON_HOST=0

usage() {
  cat <<'EOF'
Usage: smoke-sextant-remote.sh [--on-host] [--base-url URL]

Read-only checks against the Sextant remote edge.
Set SEXTANT_STATUS_TOKEN in the environment. The value is the token only,
without the "Bearer " prefix, and it is never printed.

--on-host also checks that 18046 and 18219 listen on 127.0.0.1 only.
EOF
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --on-host)
      ON_HOST=1
      shift
      ;;
    --base-url)
      if [ "$#" -lt 2 ]; then
        echo "missing URL for --base-url" >&2
        exit 2
      fi
      BASE_URL="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    --token|--token=*)
      echo "refusing a token on the command line; set SEXTANT_STATUS_TOKEN" >&2
      exit 2
      ;;
    *)
      echo "unknown argument" >&2
      usage >&2
      exit 2
      ;;
  esac
done

BASE_URL="${BASE_URL%/}"
case "$BASE_URL" in
  http://*|https://*)
    ;;
  *)
    echo "refusing base URL" >&2
    exit 2
    ;;
esac
case "$BASE_URL" in
  *[@[:space:]\"\']*)
    echo "refusing base URL" >&2
    exit 2
    ;;
esac

failures=0
workdir="$(mktemp -d)"
trap 'rm -rf "$workdir"' EXIT

ok() {
  printf 'OK: %s\n' "$1"
}

bad() {
  printf 'FAIL: %s\n' "$1" >&2
  failures=$((failures + 1))
}

request_code() {
  # $1 URL, $2 method. Writes headers to $3. Prints the status code.
  curl -sS --max-redirs 0 --connect-timeout 10 --max-time 30 \
    --user-agent sextant-remote-smoke \
    -D "$3" -o "$workdir/body" -w '%{http_code}' \
    -X "$2" "$1" || true
}

check_unauth() {
  local headers code location printable
  headers="$workdir/unauth.hdr"
  code="$(request_code "${BASE_URL}/" GET "$headers")"
  if [ "$code" != "302" ]; then
    bad "/ returned ${code:-curl-error}, expected 302"
    return
  fi
  location="$(awk 'BEGIN{IGNORECASE=1} /^Location:/ {
    sub(/\r/, "")
    sub(/^[^:]*:[[:space:]]*/, "")
    print
    exit
  }' "$headers")"
  case "$location" in
    https://auth.pericopeai.com/realms/fortress|https://auth.pericopeai.com/realms/fortress/*)
      ok "/ unauthenticated redirects to the fortress realm"
      ;;
    "")
      bad "/ returned 302 without a Location header"
      ;;
    *)
      printable="${location%%\?*}"
      bad "/ redirected to ${printable}, expected the fortress realm"
      ;;
  esac
}

check_status_no_token() {
  local code
  code="$(request_code "${BASE_URL}/status" GET "$workdir/status-none.hdr")"
  if [ "$code" = "401" ]; then
    ok "/status without a token is 401"
  else
    bad "/status without a token returned ${code:-curl-error}, expected 401"
  fi
}

check_status_with_token() {
  local code
  if [ -z "${SEXTANT_STATUS_TOKEN:-}" ]; then
    bad "/status with token: SEXTANT_STATUS_TOKEN is unset"
    return
  fi
  if ! code="$(
    SEXTANT_STATUS_URL="${BASE_URL}/status" \
    SEXTANT_STATUS_BODY="$workdir/status-body" \
    python3 - "$workdir/status-body" <<'PY'
import os
import sys
import urllib.error
import urllib.request

token = os.environ.get("SEXTANT_STATUS_TOKEN", "")
if not token or any(ch.isspace() or ch in "\\\"'" for ch in token):
    print("SEXTANT_STATUS_TOKEN is empty or not a single token", file=sys.stderr)
    sys.exit(3)

url = os.environ["SEXTANT_STATUS_URL"]
body_path = os.environ["SEXTANT_STATUS_BODY"]

class NoRedirect(urllib.request.HTTPErrorProcessor):
    def http_response(self, request, response):
        return response

    https_response = http_response

opener = urllib.request.build_opener(NoRedirect)
req = urllib.request.Request(
    url,
    method="GET",
    headers={
        "Authorization": "Bearer " + token,
        "Accept": "application/json",
        "User-Agent": "sextant-remote-smoke",
    },
)
try:
    with opener.open(req, timeout=30) as resp:
        data = resp.read(1048577)
        code = resp.status
except Exception as exc:
    print("request failed: " + type(exc).__name__, file=sys.stderr)
    sys.exit(4)

with open(body_path, "wb") as handle:
    handle.write(data[:1048576])
print(code)
PY
  )"; then
    bad "/status with token: request failed"
    return
  fi
  if [ "$code" != "200" ]; then
    bad "/status with token returned ${code}, expected 200"
    return
  fi
  if ! python3 - "$workdir/status-body" <<'PY'
import json
import sys

path = sys.argv[1]
with open(path, "rb") as handle:
    raw = handle.read(1048577)
if len(raw) > 1048576:
    sys.exit(1)
try:
    json.loads(raw.decode("utf-8"))
except Exception:
    sys.exit(1)
PY
  then
    bad "/status with token returned 200 that was not JSON"
    return
  fi
  ok "/status with token is 200 JSON"
}

check_post_status() {
  local code
  code="$(request_code "${BASE_URL}/status" POST "$workdir/status-post.hdr")"
  case "$code" in
    403|405)
      ok "POST /status is ${code}"
      ;;
    *)
      bad "POST /status returned ${code:-curl-error}, expected 403 or 405"
      ;;
  esac
}

check_healthz() {
  local code
  code="$(request_code "${BASE_URL}/healthz" GET "$workdir/healthz.hdr")"
  if [ "$code" = "404" ]; then
    ok "/healthz is 404"
  else
    bad "/healthz returned ${code:-curl-error}, expected 404"
  fi
}

check_loopback_port() {
  local port listeners addr found
  port="$1"
  if ! command -v ss >/dev/null 2>&1; then
    bad "ss is not installed"
    return
  fi
  if ! listeners="$(ss -H -ltn "sport = :${port}" | awk '{print $4}')"; then
    bad "ss failed for port ${port}"
    return
  fi
  if [ -z "$listeners" ]; then
    bad "port ${port} is not listening"
    return
  fi
  found=0
  while IFS= read -r addr; do
    if [ -z "$addr" ]; then
      continue
    fi
    if [ "$addr" != "127.0.0.1:${port}" ]; then
      bad "port ${port} is bound to ${addr}"
      return
    fi
    found=1
  done <<EOF
${listeners}
EOF
  if [ "$found" -ne 1 ]; then
    bad "port ${port} is not bound to 127.0.0.1"
    return
  fi
  ok "port ${port} is bound to 127.0.0.1 only"
}

check_unauth
check_status_no_token
check_status_with_token
check_post_status
check_healthz

if [ "$ON_HOST" -eq 1 ]; then
  check_loopback_port 18046
  check_loopback_port 18219
fi

if [ "$failures" -ne 0 ]; then
  printf 'FAIL: %s check(s) failed\n' "$failures" >&2
  exit 1
fi

printf 'OK: sextant remote smoke passed\n'
