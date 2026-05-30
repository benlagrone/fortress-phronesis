# PericopeAI Deployment (Control Plane)

This is the minimal, repeatable way to deploy the coupled PericopeAI + Solomonic Clock stack from the control-plane repo (`fortress-phronesis`) on the Contabo host.

## Components
- `mysql` (local DB, host port `3307`, data persisted to `mysql_data` volume).
- `augustine-corpus-live` (in `/root/workspace/AugustineCorpus`, internal port 8001, data persisted to `corpus_indexes` volume).
- `pericopeai-api` (backend, host port 18000).
- `solomonic-clock` (clock runtime, host port `8086`, shared network access to corpus).
- `pericopeai-frontend` (React, host port 13080).

## One-time prereqs
1) Clone repos:
   - Corpus: `/root/workspace/AugustineCorpus`
   - API: `/root/workspace/AugustineService`
   - Clock: `/root/workspace/Solomonic_Seals`
   - FE: `/root/workspace/AugustineFE`
2) Ensure `.env` files exist:
   - `/root/workspace/AugustineCorpus/.env` (corpus settings).
   - `/root/workspace/AugustineService/.env` (API, including `CORPUS_API_URL` and DB creds if overriding defaults).
   - `/root/workspace/Solomonic_Seals/.env` (clock overrides if guided prompts key is required).
   - `/root/workspace/AugustineFE/.env` (frontend build-time values and clock proxy key).
3) Network:
   ```
   docker network create fortress-phronesis-net 2>/dev/null || true
   ```

## Deploy
0) Verify deployment lock:
   ```
   bash scripts/verify-pericope-deploy-lock.sh
   ```

1) Core services (from control plane repo):
   ```
   docker compose -p fortress-phronesis -f docker-compose.pericope.yml \
     up -d --build mysql augustine-corpus-live pericopeai-api solomonic-clock
   ```
   (Optional indexer run)
   ```
   docker compose -p fortress-phronesis -f docker-compose.pericope.yml \
     --profile index run --rm pericopeai-indexer
   ```

2) Frontend (from control plane repo `/root/workspace/fortress-phronesis`):
   ```
   docker compose --env-file /root/workspace/AugustineFE/.env \
     -p fortress-phronesis -f docker-compose.pericope.yml \
     up -d --build pericopeai-frontend
   ```

3) Frontend-only GitHub Actions redeploy:
   - Workflow: `.github/workflows/deploy-pericope-frontend.yml`
   - Use this when frontend/public media files need to be republished without waiting for a full corpus/API rollout.

## API & Frontend specifics
- Build contexts (hard-coded in compose):
  - API: `/root/workspace/AugustineService` (uses `/root/workspace/AugustineService/.env`)
  - Clock: `/root/workspace/Solomonic_Seals`
  - FE:  `/root/workspace/AugustineFE` (build args come from `docker-compose.pericope.yml`; set `REACT_APP_*` there or in the FE Dockerfile ARGs)
- Key API envs:
  - `CORPUS_API_URL=http://augustine-corpus-live:8001`
  - DB defaults (if not overridden): `MYSQL_HOST=mysql`, `MYSQL_DB=augustine_chat`, `MYSQL_USER=augustine`, `MYSQL_PASS=password`, `MYSQL_ROOT_PASSWORD=rootpass`
- Key FE build args (to avoid mixed-content/CORS):
  - `REACT_APP_ROOT_URL=https://pericopeai.com` (API base through nginx `/api`)
  - `REACT_APP_ENVIRONMENT=prd`
  - `REACT_APP_KEYCLOAK_URL=https://auth.pericopeai.com`
  - `REACT_APP_KEYCLOAK_REALM=pericope`
  - `REACT_APP_KEYCLOAK_CLIENT_ID=pericope-web`
- Ports:
  - DB: host `3307` → container `3306`
  - API: host `18000` → container `8080`
  - Clock: host `8086` → container `8080`
  - FE:  host `13080` → container `80`

## Redeploy / rebuild
- Core service redeploy:
  ```
  docker compose -p fortress-phronesis -f docker-compose.pericope.yml \
    up -d --build mysql augustine-corpus-live pericopeai-api solomonic-clock
  ```
  (Re-run indexer if needed.)
- Frontend redeploy:
  ```
  docker compose --env-file /root/workspace/AugustineFE/.env \
    -p fortress-phronesis -f docker-compose.pericope.yml \
    up -d --build pericopeai-frontend
  ```

## Verify
```
curl -I http://127.0.0.1:8086/api/clock     # clock
curl -I http://127.0.0.1:18000/api/docs     # API
curl -I http://127.0.0.1:13080              # FE
mysql -h 127.0.0.1 -P 3307 -u${MYSQL_USER:-augustine} -p   # DB (requires mysql client)
```

## Nginx (host)
Point upstreams to:
```
upstream pericope_api { server 127.0.0.1:18000; }
upstream pericope_fe  { server 127.0.0.1:13080; }
```
Routes:
```
location = /api/pericope/guided-prompts { proxy_pass http://pericope_fe; }
location /api { proxy_pass http://pericope_api; }
location /    { proxy_pass http://pericope_fe; }
```
Reload after edits: `nginx -t && nginx -s reload`.

Ordering rule:
- Keep the exact-match `location = /api/pericope/guided-prompts` block before the generic `location /api` block so guided prompts reach the frontend/clock path instead of the API container.

## Notes
- The corpus container is internal-only (no host port). If you need host access, add `ports: ["8001:8001"]` in `docker-compose.corpus.yml`.
- Ensure `CORPUS_API_URL` in the API env points to `http://augustine-corpus-live:8001`.
- Shared network is `fortress-phronesis-net`.
- Healthcheck on corpus is enabled; API/FE use compose defaults. Use `docker compose -p fortress-phronesis -f docker-compose.pericope.yml logs -f` for runtime logs.
- MySQL data persists to the `mysql_data` volume. Rotate DB creds in `.env` before first run.

---

## Deployment Discipline Addendum (Authoritative for Strategy Changes)

This addendum captures updated deployment strategy rules in detail while keeping the original quick-start guide above.

### A) Release Types

1. Code Release
   - API/FE/runtime behavior changes.
   - Rebuild/redeploy affected services.
2. Data Release
   - Author/corpus/index updates.
   - Default path: author-scoped indexing only.
3. Full Reindex
   - Exceptional only.
   - Must be explicitly invoked and documented.

### B) Environment and Build Rules

1. `.env` is authoritative per repo:
   - `/root/workspace/AugustineService/.env`
   - `/root/workspace/AugustineCorpus/.env`
   - `/root/workspace/Solomonic_Seals/.env`
   - `/root/workspace/AugustineFE/.env`
2. Do not use ad-hoc shell exports for deployment behavior.
3. FE `REACT_APP_*` values are build-time only.
4. FE builds must use explicit env file:

```bash
docker compose --env-file /root/workspace/AugustineFE/.env \
  -p fortress-phronesis -f docker-compose.pericope.yml \
  up -d --build pericopeai-frontend
```

5. If shell overrides are suspected, clear them before FE build:

```bash
unset REACT_APP_AUGUSTINE_API_KEY REACT_APP_ENVIRONMENT REACT_APP_API_BASE_URL REACT_APP_ROOT_URL
```

### C) Preflight Gates (Required)

Run before every deploy:

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
grep -E '^(SOLOMONIC_GUIDED_PROMPTS_API_KEY|SOLOMONIC_PSALM_SOURCE_MODE|SOLOMONIC_PERICOPE_API_BASE)=' /root/workspace/Solomonic_Seals/.env
grep -E '^(REACT_APP_ENVIRONMENT|REACT_APP_AUGUSTINE_API_KEY|REACT_APP_KEYCLOAK_URL)=' /root/workspace/AugustineFE/.env
```

Key alignment check (`AUGUSTINE_API_KEYS` contains FE key):

```bash
svc="$(grep -m1 '^AUGUSTINE_API_KEYS=' /root/workspace/AugustineService/.env | cut -d= -f2-)"
fe="$(grep -m1 '^REACT_APP_AUGUSTINE_API_KEY=' /root/workspace/AugustineFE/.env | cut -d= -f2-)"
[ -n "$svc" ] && [ -n "$fe" ] || { echo "ERROR: key missing/empty"; exit 1; }
printf '%s\n' "$svc" | tr ',' '\n' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//' | grep -Fxq -- "$fe"
```

### D) Data Release Default (Author-Scoped Indexing)

For author additions or targeted updates, do not run a full index by default:

```bash
cd /root/workspace/fortress-phronesis
COMPOSE="docker compose -p fortress-phronesis -f docker-compose.pericope.yml"

$COMPOSE --profile index run --rm pericopeai-indexer \
  python preprocess_and_index.py \
  --author <author_slug> \
  --texts-root /app/texts \
  --index-dir /app/indexes/<author_slug>

$COMPOSE restart augustine-corpus-live pericopeai-api
```

### E) Mandatory Smoke Gates (Pass/Fail)

Gate 1: local health

```bash
curl -fsS http://127.0.0.1:18000/api/healthz
curl -fsS http://127.0.0.1:18000/api/v1/authors >/dev/null
curl -fsS http://127.0.0.1:8086/api/clock >/dev/null
```

Gate 2: direct chat against API port

```bash
KEY="$(grep -m1 '^AUGUSTINE_API_KEYS=' /root/workspace/AugustineService/.env | cut -d= -f2- | cut -d, -f1)"
curl -sS -m 120 \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $KEY" \
  -d '{"question":"health probe","mode":"conversation","persona":"augustine"}' \
  http://127.0.0.1:18000/api/v2/chat >/dev/null
```

Gate 3: public chat through nginx

```bash
curl -sS -m 180 \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $KEY" \
  -d '{"question":"health probe","mode":"conversation","persona":"augustine"}' \
  https://pericopeai.com/api/v2/chat >/dev/null
```

### F) Nginx `/api` Requirements

For chat workloads, configure `/api` with:

1. `proxy_connect_timeout 10s`
2. `proxy_send_timeout 300s`
3. `proxy_read_timeout 300s`
4. `proxy_set_header Authorization $http_authorization;`

Routing order must also preserve:

```nginx
location = /api/pericope/guided-prompts {
    proxy_pass http://pericope_fe;
}

location /api {
    proxy_pass http://pericope_api;
}
```

Validate and reload:

```bash
sudo nginx -t && sudo systemctl reload nginx
```

### G) Rollback Discipline

1. Define rollback target before deploy.
2. Rebuild/restart affected services using canonical compose commands.
3. Re-run smoke gates after rollback.
4. If failure came from data release, restore prior index/data snapshot and restart corpus/api.

### H) Related Policy

Developer operational rules are maintained in:

- `docs/developer-guide.md`
