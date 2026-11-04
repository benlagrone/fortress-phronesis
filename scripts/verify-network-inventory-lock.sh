#!/bin/bash
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/.." && pwd)
python3 - "$ROOT" <<'PY'
import json,pathlib,sys
root=pathlib.Path(sys.argv[1]);lock=pathlib.Path('/Users/benjaminlagrone/Documents/projects/workspace-deployment/locks/network-inventory.yaml')
d=json.loads(lock.read_text());assert d['runtime_host']=='fortress.sextant';assert d['compose_project']=='fortress-network-inventory';assert d['compose_file']=='docker-compose.network-inventory.yml'
s=(root/d['compose_file']).read_text();assert '127.0.0.1:18160:18160' in s;assert 'fortress-network-inventory-net' in s;assert 'docker.sock' not in s
assert 'fortress-sextant:network-inventory' in s
print('Fortess DNA deployment contract verified.')
PY
