#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
compose_file="${root}/docker-compose.fortresslegaltech.yml"
app_manifest="${root}/deploy/apps/fortresslegaltech.yaml"
nginx_bootstrap="${root}/deploy/nginx/fortresslegaltech.com.bootstrap.conf"
nginx_tls="${root}/deploy/nginx/fortresslegaltech.com.conf"
runbook="${root}/docs/fortresslegaltech-deployment.md"

for file in "$compose_file" "$app_manifest" "$nginx_bootstrap" "$nginx_tls" "$runbook"; do
  test -f "$file" || { echo "FAIL: missing ${file}" >&2; exit 1; }
done

grep -Fq 'ghcr.io/benlagrone/fortresslegaltech' "$compose_file"
grep -Fq '"127.0.0.1:18042:8080"' "$compose_file"
grep -Fq 'project_name: fortresslegaltech' "$app_manifest"
grep -Fq 'host_bind: 127.0.0.1:18042' "$app_manifest"
grep -Fq 'server_name fortresslegaltech.com www.fortresslegaltech.com;' "$nginx_bootstrap"
grep -Fq 'proxy_pass http://127.0.0.1:18042;' "$nginx_bootstrap"
grep -Fq '/etc/letsencrypt/live/fortresslegaltech.com/fullchain.pem' "$nginx_tls"
grep -Fq 'Compose project: `fortresslegaltech`' "$runbook"

if grep -Eq '(^|[[:space:]])18042:8080' "$compose_file"; then
  echo "FAIL: public host binding detected; port 18042 must be loopback-only" >&2
  exit 1
fi

echo "PASS: Fortress Legal Technologies deployment lock"

