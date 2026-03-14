# Local Pericope Stack Runbook

Purpose: define one repeatable local container practice for PericopeAI and keep it separate from the remote `fortress-phronesis` deployment contract.

## Rules

1. Local standalone development uses the compose files in `AugustineCorpus/`, `AugustineService/`, and `AugustineFE/`.
2. Dev server and prod deployment use `fortress-phronesis/docker-compose.pericope.yml`.
3. Do not mix the two contracts in the same command sequence.
4. Do not use ad-hoc `docker network connect`, manual network aliases, or inline env overrides as normal practice.
5. If a local stack requires a manual recovery step, fix compose or the runbook before calling the workflow valid.

## Environment Split

Local standalone dev (macOS)
- Workspace root: `/Users/benjaminlagrone/Documents/projects/pericopeai.com`
- Corpus compose: `AugustineCorpus/docker-compose.corpus.yml`
- API compose: `AugustineService/docker-compose.yml`
- Frontend compose: `AugustineFE/docker-compose.yml`
- Shared Docker network: `pericope_net`

Dev server / prod-like deploy
- Stack root: `fortress-phronesis`
- Compose file: `fortress-phronesis/docker-compose.pericope.yml`
- Shared Docker network: `fortress-phronesis-net`

Production
- Same compose contract as dev server
- Use the versioned release runbooks and deployment guides in this docs directory

## Local Contract

Expected local container names
- `pericopeai-corpus-corpus-1`
- `augustineservice-api-1`
- `augustinefe-frontend-1`
- `augustineservice-mysql-1`

Expected local ports
- Corpus: `8001`
- API: `8080`
- Frontend: `13080`
- Local standalone MySQL: `3308`

Local service wiring
- Corpus service name on `pericope_net`: `corpus`
- API alias on `pericope_net`: `pericopeai-api`
- Frontend nginx proxies `/api` to `http://pericopeai-api:8080`
- API talks to corpus at `http://corpus:8001`
- Local frontend build disables Keycloak by default with `REACT_APP_DISABLE_AUTH=true`
- Local API startup bootstraps MySQL automatically by running `python create_tables.py`
- API `/healthz` and `/api/healthz` now include `db.ok`

Why this matters
- Local standalone must not depend on `augustine-corpus-live`, `fortress-phronesis-net`, or host port `3307`
- `3307` is reserved by the `fortress-phronesis` stack on this machine
- Frontend host port `13080` is shared with the control-plane mirror contract, so do not run both Pericope frontend stacks at the same time

## Local Startup

Run from `/Users/benjaminlagrone/Documents/projects/pericopeai.com`:

```bash
docker network create pericope_net >/dev/null 2>&1 || true

docker compose -f AugustineCorpus/docker-compose.corpus.yml up -d --build corpus
docker compose -f AugustineService/docker-compose.yml up -d --build
docker compose -f AugustineFE/docker-compose.yml up -d --build frontend
```

## Local Smoke Tests

```bash
curl -sS http://localhost:8001/healthz
curl -sS http://localhost:8080/healthz
curl -sS http://localhost:13080

curl -sS http://localhost:8080/api/v1/scripture/verse \
  -H 'Content-Type: application/json' \
  -d '{"reference":"John 1:1","translation":"kjv"}'

curl -sS http://localhost:13080/api/v1/scripture/verse \
  -H 'Content-Type: application/json' \
  -d '{"reference":"John 1:1","translation":"kjv"}'
```

The verse response should include:
- `reference: "John 1:1"`
- `source_witness.id: "vulgate"` when local scripture source data is mounted
- translations including `kjv` and `drc`

The API health response should include:
- `ok: true`
- `db.ok: true`
- `environment: "dev"`

## Local SQL Validation

Use this when you need to verify DB-backed flows, not just HTTP reachability:

```bash
cd /Users/benjaminlagrone/Documents/projects/pericopeai.com/AugustineService

docker compose -f docker-compose.yml exec -T mysql sh -lc '
DB="${MYSQL_DATABASE:-augustine_chat}"
mysql -h127.0.0.1 -uroot -p"$MYSQL_ROOT_PASSWORD" -D "$DB" -e "
SHOW TABLES LIKE '\''users'\'';
SHOW TABLES LIKE '\''sessions'\'';
SHOW TABLES LIKE '\''messages'\'';
SHOW TABLES LIKE '\''citations'\'';
"
'
```

Expected result:
- all four tables exist in `augustine_chat`
- if they do not, local startup is not healthy even if the API container is running

## Local Stop / Rebuild

Stop services:

```bash
docker compose -f AugustineFE/docker-compose.yml down
docker compose -f AugustineService/docker-compose.yml down
docker compose -f AugustineCorpus/docker-compose.corpus.yml down
```

Rebuild a single service:

```bash
docker compose -f AugustineCorpus/docker-compose.corpus.yml up -d --build corpus
docker compose -f AugustineService/docker-compose.yml up -d --build mysql api
docker compose -f AugustineFE/docker-compose.yml up -d --build frontend
```

## Local Env Ownership

`AugustineCorpus/.env`
- Corpus runtime settings only
- Do not use it to point local API at remote service names

`AugustineService/.env`
- API runtime settings only
- Local standalone compose hard-codes local `CORPUS_API_URL=http://corpus:8001`
- Do not set local standalone expectations to `http://augustine-corpus-live:8001`

`AugustineFE/.env`
- Frontend build/runtime settings only
- Local standalone frontend should use proxied `/api`
- Do not rely on `REACT_APP_ROOT_URL=https://pericopeai.com` for local container builds

## Forbidden Local Practices

Do not do these in the normal local workflow:
- `docker network connect ...`
- `docker network connect --alias ...`
- `CORPUS_API_URL=... docker compose ...`
- `REACT_APP_ROOT_URL=... docker compose ...`
- using `fortress-phronesis/docker-compose.pericope.yml` as the default local dev stack
- expecting local standalone MySQL to bind `3307`

If one of these seems necessary, the local contract is drifting and must be fixed in compose/docs first.

## Dev Server Contract

Use this when operating the shared dev server at `192.168.86.23`:
- Compose file: `fortress-phronesis/docker-compose.pericope.yml`
- Ports: API `18000`, FE `13080`, MySQL `3307`
- Network: `fortress-phronesis-net`
- Canonical guide: [dev-server-container-runbook.md](dev-server-container-runbook.md)

Required commands come from the control-plane runbooks, not the standalone local compose files.

## Production Contract

Use this when deploying prod on `vmi2669159`:
- Compose file: `fortress-phronesis/docker-compose.pericope.yml`
- Network: `fortress-phronesis-net`
- Frontend env file: `/root/workspace/AugustineFE/.env`
- Canonical guides:
  - [pericopeai-deployment.md](pericopeai-deployment.md)
  - [release-runbook-prod-v1.1.2.md](release-runbook-prod-v1.1.2.md)
  - [server-environments.md](server-environments.md)

Prod rules remain:
- no ad-hoc env injection
- no live container mutation as deployment strategy
- always run deploy lock verification first

## Decision Rule

Use this quick check before acting:

- If API/MySQL are `8080` and `3308`, use the local standalone runbook.
- If API/MySQL are `18000` and `3307`, use the `fortress-phronesis` deployment runbooks.
- Frontend host port `13080` is not enough by itself to identify the environment.
- If a command mentions `augustine-corpus-live` or `fortress-phronesis-net`, it is not the local standalone workflow.
