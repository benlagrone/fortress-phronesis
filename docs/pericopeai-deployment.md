# PericopeAI Deployment (Control Plane)

This is the minimal, repeatable way to deploy the PericopeAI stack from the control-plane repo (`fortress-phronesis`) on the Contabo host.

## Components
- `augustine-corpus-live` (in `/root/workspace/AugustineCorpus`, internal port 8001, data persisted to `corpus_indexes` volume).
- `pericopeai-api` (backend, host port 18000).
- `pericopeai-frontend` (React, host port 13080).

## One-time prereqs
1) Clone repos:
   - Corpus: `/root/workspace/AugustineCorpus`
   - API: `/root/workspace/AugustineService`
   - FE: `/root/workspace/AugustineFE`
2) Ensure `.env` files exist:
   - `/root/workspace/AugustineCorpus/.env` (corpus settings).
   - `/root/workspace/AugustineService/.env` (API, including `CORPUS_API_URL`).
3) Network:
   ```
   docker network create pericope_net 2>/dev/null || true
   ```

## Deploy
1) Corpus (from control plane repo):
   ```
   docker compose -f docker-compose.corpus.yml up -d --build augustine-corpus-live
   ```
   (Optional indexer run)
   ```
   docker compose -f docker-compose.corpus.yml --profile index run --rm pericopeai-indexer
   ```

2) API + Frontend (from control plane repo `/root/workspace/fortress-phronesis`):
   ```
   docker compose -f docker-compose.pericope.yml up -d --build pericopeai-api pericopeai-frontend
   ```

## API & Frontend specifics
- Build contexts (hard-coded in compose):
  - API: `/root/workspace/AugustineService` (uses `/root/workspace/AugustineService/.env`)
  - FE:  `/root/workspace/AugustineFE` (build args come from `docker-compose.pericope.yml`; set `REACT_APP_*` there or in the FE Dockerfile ARGs)
- Key API envs:
  - `CORPUS_API_URL=http://augustine-corpus-live:8001`
  - DB creds in `/root/workspace/AugustineService/.env`
- Key FE build args (to avoid mixed-content/CORS):
  - `REACT_APP_ROOT_URL=https://pericopeai.com` (API base through nginx `/api`)
  - `REACT_APP_ENVIRONMENT=prd`
  - `REACT_APP_KEYCLOAK_URL=https://auth.pericopeai.com`
  - `REACT_APP_KEYCLOAK_REALM=pericope`
  - `REACT_APP_KEYCLOAK_CLIENT_ID=pericope-web`
- Ports:
  - API: host `18000` → container `8080`
  - FE:  host `13080` → container `80`

## Redeploy / rebuild
- Corpus redeploy:
  ```
  docker compose -f docker-compose.corpus.yml up -d --build augustine-corpus-live
  ```
  (Re-run indexer if needed.)
- API/FE redeploy:
  ```
  docker compose -f docker-compose.pericope.yml up -d --build pericopeai-api pericopeai-frontend
  ```

## Verify
```
curl -I http://127.0.0.1:8001/healthz        # corpus
curl -I http://127.0.0.1:18000/api/docs      # API
curl -I http://127.0.0.1:13080               # FE
```

## Nginx (host)
Point upstreams to:
```
upstream pericope_api { server 127.0.0.1:18000; }
upstream pericope_fe  { server 127.0.0.1:13080; }
```
Routes:
```
location /api { proxy_pass http://pericope_api; }
location /    { proxy_pass http://pericope_fe; }
```
Reload after edits: `nginx -t && nginx -s reload`.

## Notes
- The corpus container is internal-only (no host port). If you need host access, add `ports: ["8001:8001"]` in `docker-compose.corpus.yml`.
- Ensure `CORPUS_API_URL` in the API env points to `http://augustine-corpus-live:8001`.
- Healthcheck on corpus is enabled; API/FE use compose defaults. Use `docker compose -f docker-compose.pericope.yml logs -f` for runtime logs.
