# Deployment Handoff (Codex)

## Purpose
This repo is a control-plane. The main deployment helper for PericopeAI in this tree is:
`scripts/deploy-pericopeai-prod.sh`.

This handoff is for Codex agents working in application developer mode so they remember
what the script does and how to report deployment results back into this repo.

## What `scripts/deploy-pericopeai-prod.sh` does
Target: the PericopeAI backend repo (default `/root/workspace/AugustineService` or a
macOS fallback).

Steps (in order):
1) Validate required commands (`git`, `docker`, `curl`).
2) `git pull --ff-only` in the backend repo.
3) `docker compose down` for the stack in that repo.
4) `docker compose up -d` for the DB service.
5) `docker compose up -d --build` for the API service.
6) Run DB migrations in the API container (`python create_tables.py` by default).
7) Hit a health endpoint (default `http://localhost:8080/api/healthz`).

It uses the backend repo’s `.env` and expects the repo’s own `docker-compose.yml`
unless `COMPOSE_FILE` is overridden.

## Environment overrides
All can be set when invoking the script:
- `APP_PATH` (backend repo path)
- `COMPOSE_FILE` (compose filename)
- `API_SERVICE` (default `api`)
- `DB_SERVICE` (default `mysql`)
- `HEALTH_URL` (default `http://localhost:8080/api/healthz`)
- `CREATE_TABLES_CMD` (default `python create_tables.py`)

## Usage examples
```bash
bash scripts/deploy-pericopeai-prod.sh

APP_PATH=/root/workspace/AugustineService \
COMPOSE_FILE=docker-compose.yml \
API_SERVICE=api \
DB_SERVICE=mysql \
HEALTH_URL=http://localhost:8080/api/healthz \
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
```
