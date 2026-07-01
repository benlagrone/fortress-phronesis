# Deployment Handoff (Codex)

## Purpose
This repo is a control-plane. The main deployment helper for PericopeAI in this tree is:
`scripts/deploy-pericopeai-prod.sh`.

This handoff is for Codex agents working in application developer mode so they remember
what the script does and how to report deployment results back into this repo.

## What `scripts/deploy-pericopeai-prod.sh` does
Target: the PericopeAI backend repo (default sibling `AugustineService`) deployed
through the locked `fortress-phronesis` compose stack.

Steps (in order):
1) Validate required commands (`git`, `docker`, `curl`).
2) Run `scripts/verify-pericope-deploy-lock.sh`.
3) Fetch and fast-forward/validate the backend repo branch, unless explicitly skipped.
4) Rebuild and start `pericopeai-api` with:
   `docker compose -p fortress-phronesis -f docker-compose.pericope.yml up -d --build pericopeai-api`
5) Run DB migrations in the API container (`python create_tables.py` by default).
6) Sync the author catalog against `augustine-corpus-live`.
7) Smoke local API health/authors and the host TLS vhost via `--resolve`.

It uses the backend repo’s `.env` through `docker-compose.pericope.yml`. It must not
deploy the old standalone `AugustineService/docker-compose.yml` stack.

## Environment overrides
All can be set when invoking the script:
- `APP_PATH` (backend repo path)
- `APP_REPO_URL` (backend repo remote)
- `APP_REF` (default `master`)
- `SOURCE_SHA` (optional exact commit)
- `COMPOSE_PROJECT` (default `fortress-phronesis`)
- `COMPOSE_FILE` (default `docker-compose.pericope.yml`)
- `API_SERVICE` (default `pericopeai-api`)
- `HEALTH_URL` (default `http://127.0.0.1:18000/api/healthz`)
- `AUTHORS_URL` (default `http://127.0.0.1:18000/api/v1/authors`)
- `PUBLIC_HOST` (default `pericopeai.com`)
- `PUBLIC_RESOLVE_IP` (default `127.0.0.1`)
- `CREATE_TABLES_CMD` (default `python create_tables.py`)
- `SYNC_AUTHOR_CATALOG_CMD`
- `SKIP_GIT_SYNC=true`
- `SKIP_MIGRATIONS=true`
- `SKIP_AUTHOR_SYNC=true`
- `SKIP_PUBLIC_SMOKE=true`

## Usage examples
```bash
bash scripts/deploy-pericopeai-prod.sh

APP_PATH=/root/workspace/AugustineService \
APP_REF=master \
bash scripts/deploy-pericopeai-prod.sh
```

## Writing handoffs back to this repo
When you deploy or modify deployment logic, append a short update log in this file
under the Handoff Log section. Keep it brief and operational.

Required fields:
- Date/time (UTC)
- What changed (script changes or deploy actions)
- Outcome (success/fail, health check status)
- Follow-ups (if any)

## GitHub Workflow Guardrails

`.github/workflows/deploy-pericope-api.yml` deploys through the same locked
compose project. If `/root/workspace/fortress-phronesis` is dirty on the server,
the workflow preserves it and uses `/root/workspace/fortress-phronesis-deploy`
as a clean deploy checkout so local server edits do not block production API
deployment. The workflow also restores preserved service `.env` files with a
passwordless-sudo fallback because production env files may be owned by a
different server user.

## Gateway (CorpusGateway)
- Repo path: `CorpusGateway/` (sibling to AugustineService).
- Build artifact: `Dockerfile` in `CorpusGateway/`; image typically tagged `corpus-gateway`.
- Compose: `docker-compose.gateway.yml` in this repo (service `corpus-gateway`).
- Ports: host 18002 -> container 8001 (edit `docker-compose.gateway.yml` if needed).
- Health: `GET /healthz` (lists persona slugs).
- Config: dynamic load from `CORPUS_BASE_URL/v1/authors`; no static maps. Ensure
  `CORPUS_BASE_URL` points to the live corpus/gateway network target.
- Deploy/update steps (outcome-focused): produce a refreshed gateway image from
  `CorpusGateway/`, run via `docker compose -f docker-compose.gateway.yml up -d --build`,
  and confirm `/healthz` succeeds and shows expected personas.

## Handoff log
Append entries below:

```
2025-01-01T00:00Z
Change: Example only.
Outcome: Success. Health check OK.
Follow-ups: None.
2025-12-22T00:00Z
Change: Added CorpusGateway service/docs and routed API book/book_partial through corpus; no production deploy run here.
Outcome: Not deployed from control plane; manual docker compose rebuilds only. Health not checked via deploy script.
Follow-ups: Run scripts/deploy-pericopeai-prod.sh pointing API at the gateway/corpus once ready.
2025-12-22T23:00Z
Change: Documented CorpusGateway deployment context (path, ports, health, config) and API book/book_partial proxying. No control-plane deploy run here.
Outcome: Gateway/API rebuilt manually; `/healthz` returns personas. Control-plane deploy script unchanged.
Follow-ups: When deploying via control plane, ensure `CORPUS_BASE_URL` is set for gateway and API `CORPUS_API_URL` points at the gateway; verify gateway `/healthz` and API `/api/healthz`.
2026-07-01T00:00Z
Change: Repointed `scripts/deploy-pericopeai-prod.sh` from the legacy standalone AugustineService compose stack to the locked `fortress-phronesis` compose path for `pericopeai-api`.
Outcome: Script now verifies the deployment lock, validates/syncs the backend checkout, rebuilds `pericopeai-api`, runs migrations/catalog sync, and smokes container plus host-vhost health.
Follow-ups: Keep API fixes deployable through Fortress Phronesis; do not use the legacy standalone compose path for production API deploys.
```
