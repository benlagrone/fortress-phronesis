# PericopeAI Deployment Strategy and Guide

This document is the canonical deployment strategy for PericopeAI on Contabo.
It defines release types, immutable rules, preflight gates, rollout steps, and rollback.

## 1) Strategy Overview

Deployments are split into two release types:

1. Code Release
   - Changes API, frontend, runtime config, routing logic, auth logic.
   - May rebuild `pericopeai-api` and `pericopeai-frontend` images/containers.
2. Data Release
   - Changes corpus content/indexes/service packs (for example adding authors).
   - Must default to author/service-scoped indexing.
   - Must not imply full reindex unless explicitly requested.

Primary objective: deterministic deploys with low drift and fast rollback.

## 2) Non-Negotiable Rules

1. Use one compose project and file:
   - project: `fortress-phronesis`
   - file: `docker-compose.pericope.yml`
2. Use per-repo env files only:
   - `/root/workspace/AugustineService/.env`
   - `/root/workspace/AugustineCorpus/.env`
   - `/root/workspace/AugustineFE/.env`
3. Do not rely on ad-hoc shell exports for deploy behavior.
4. Frontend `REACT_APP_*` values are build-time inputs, not runtime toggles.
5. Always pass FE env file explicitly when building frontend:
   - `docker compose --env-file /root/workspace/AugustineFE/.env ...`
6. Do not run implicit full reindex during author additions.
7. Every deploy must pass preflight and smoke gates before sign-off.

## 3) Environment Precedence and Drift Controls

Compose interpolation can use shell env first, then env files/defaults. To prevent shell override drift:

1. Before FE builds, clear shell overrides:
   - `unset REACT_APP_AUGUSTINE_API_KEY REACT_APP_ENVIRONMENT REACT_APP_API_BASE_URL REACT_APP_ROOT_URL`
2. Build FE only with `--env-file /root/workspace/AugustineFE/.env`.
3. Verify lock contract before any deploy:
   - `bash scripts/verify-pericope-deploy-lock.sh`

## 4) Canonical Paths (Prod)

1. Workspace root: `/root/workspace`
2. Stack root: `/root/workspace/fortress-phronesis`
3. Repos:
   - `/root/workspace/AugustineService`
   - `/root/workspace/AugustineCorpus`
   - `/root/workspace/AugustineFE`

## 5) Preflight Gate (Required)

Run from stack root:

```bash
cd /root/workspace/fortress-phronesis
COMPOSE="docker compose -p fortress-phronesis -f docker-compose.pericope.yml"
FE_COMPOSE="docker compose --env-file /root/workspace/AugustineFE/.env -p fortress-phronesis -f docker-compose.pericope.yml"

bash scripts/verify-pericope-deploy-lock.sh
$COMPOSE config >/tmp/pericope-config.yaml
```

Required env checks:

```bash
grep -E '^(ENV|ENVIRONMENT|HIDE_LOCAL_ONLY)=' /root/workspace/AugustineService/.env
grep -E '^(ENV|ENVIRONMENT)=' /root/workspace/AugustineCorpus/.env
grep -E '^(REACT_APP_ENVIRONMENT|REACT_APP_AUGUSTINE_API_KEY|REACT_APP_KEYCLOAK_URL)=' /root/workspace/AugustineFE/.env
```

Key-alignment check (service key list contains FE key):

```bash
svc="$(grep -m1 '^AUGUSTINE_API_KEYS=' /root/workspace/AugustineService/.env | cut -d= -f2-)"
fe="$(grep -m1 '^REACT_APP_AUGUSTINE_API_KEY=' /root/workspace/AugustineFE/.env | cut -d= -f2-)"
[ -n "$svc" ] && [ -n "$fe" ] || { echo "ERROR: key missing/empty"; exit 1; }
printf '%s\n' "$svc" | tr ',' '\n' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//' | grep -Fxq -- "$fe"
```

## 6) Code Release Procedure

Use this for API/FE/runtime changes.

```bash
cd /root/workspace/fortress-phronesis
COMPOSE="docker compose -p fortress-phronesis -f docker-compose.pericope.yml"
FE_COMPOSE="docker compose --env-file /root/workspace/AugustineFE/.env -p fortress-phronesis -f docker-compose.pericope.yml"

unset REACT_APP_AUGUSTINE_API_KEY REACT_APP_ENVIRONMENT REACT_APP_API_BASE_URL REACT_APP_ROOT_URL

$COMPOSE up -d --build mysql augustine-corpus-live pericopeai-api
$FE_COMPOSE up -d --build --force-recreate --no-deps pericopeai-frontend
$COMPOSE ps
```

## 7) Data Release Procedure (Author Additions / Corpus Updates)

Default path is additive and author-scoped.

1. Sync new texts/metadata.
2. Build only changed author index(es):

```bash
cd /root/workspace/fortress-phronesis
COMPOSE="docker compose -p fortress-phronesis -f docker-compose.pericope.yml"

$COMPOSE --profile index run --rm pericopeai-indexer \
  python preprocess_and_index.py \
  --author <author_slug> \
  --texts-root /app/texts \
  --index-dir /app/indexes/<author_slug>
```

3. Restart serving components:

```bash
$COMPOSE restart augustine-corpus-live pericopeai-api
```

Full reindex is exceptional and must be explicit.

## 8) Mandatory Smoke Gates (Release Pass/Fail)

Gate A: local API health

```bash
curl -fsS http://127.0.0.1:18000/api/healthz
curl -fsS http://127.0.0.1:18000/api/v1/authors >/dev/null
```

Gate B: direct chat against API host port

```bash
KEY="$(grep -m1 '^AUGUSTINE_API_KEYS=' /root/workspace/AugustineService/.env | cut -d= -f2- | cut -d, -f1)"
curl -sS -m 120 \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $KEY" \
  -d '{"question":"health probe","mode":"conversation","persona":"augustine"}' \
  http://127.0.0.1:18000/api/v2/chat >/dev/null
```

Gate C: public path through nginx

```bash
curl -sS -m 180 \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $KEY" \
  -d '{"question":"health probe","mode":"conversation","persona":"augustine"}' \
  https://pericopeai.com/api/v2/chat >/dev/null
```

If Gate B passes but Gate C fails, troubleshoot nginx/proxy only.

## 9) Nginx Requirements for `/api`

Pericope vhost must proxy `/api` to `127.0.0.1:18000` and set conservative long-read timeouts:

1. `proxy_connect_timeout 10s`
2. `proxy_send_timeout 300s`
3. `proxy_read_timeout 300s`
4. forward `Authorization` header:
   - `proxy_set_header Authorization $http_authorization;`

Validate after changes:

```bash
sudo nginx -t && sudo systemctl reload nginx
```

## 10) Rollback Procedure

Rollback should restore last known-good runtime quickly:

1. Revert to previous known-good code state for changed repos.
2. Rebuild/restart affected services:

```bash
cd /root/workspace/fortress-phronesis
COMPOSE="docker compose -p fortress-phronesis -f docker-compose.pericope.yml"
FE_COMPOSE="docker compose --env-file /root/workspace/AugustineFE/.env -p fortress-phronesis -f docker-compose.pericope.yml"

$COMPOSE up -d --build pericopeai-api augustine-corpus-live
$FE_COMPOSE up -d --build --force-recreate --no-deps pericopeai-frontend
```

3. Re-run smoke gates A/B/C.
4. If rollback includes data regression, restore previous index/data snapshot and restart corpus/api.

## 11) Sign-off Checklist

A deploy is complete only when all are true:

1. Preflight gate passed.
2. Services healthy in compose `ps`.
3. Smoke gates A/B/C passed.
4. No blocking errors in:
   - `pericopeai-api` logs
   - `augustine-corpus-live` logs
   - nginx error log
5. Rollback target is documented before release close.

