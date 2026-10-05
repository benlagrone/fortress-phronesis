# Solar Potential Deployment Contract

This file defines the fortress-side deployment contract for the Solar Buddy /
Solar Potential stack when it is served from the Contabo container host.

It follows the same split control-plane pattern used by Energy Data Explorer:

- the frontend repo publishes a GHCR image
- the backend repo publishes a GHCR image
- fortress deploys those images onto the target host through one shared compose file

## Current Intent

Solar Potential is split into two deploy targets:

- frontend runtime for the Solar Buddy UI
- backend runtime for the FastAPI service

Canonical source repos:

- frontend: `https://github.com/benlagrone/solar-potential-frontend`
- backend: `https://github.com/benlagrone/solar-potential-backend`

The public hostname contract is not locked in this repo yet. Fortress therefore
locks the container runtime, image names, compose file, service names, and host
ports first. Once the exact public hostname set is confirmed, update this file,
the app manifests, and host Nginx config together.

## Runtime Contract

Shared compose contract:

- Compose file: `docker-compose.solar-potential.yml`
- Compose project: `solar-potential`
- Optional server-local env file: `.env.solar-potential.local`

Frontend runtime:

- Service: `solar-potential-frontend`
- Host bind: `127.0.0.1:18030`
- Container port: `80`
- Host Nginx upstream: `http://127.0.0.1:18030`
- Image contract: `ghcr.io/benlagrone/solar-potential-frontend:sha-<commit>`

Backend runtime:

- Service: `solar-potential-backend`
- Host bind: `127.0.0.1:18031`
- Container port: `8000`
- Host Nginx upstream: `http://127.0.0.1:18031`
- Image contract: `ghcr.io/benlagrone/solar-potential-api:sha-<commit>`

Expected host routing after cutover:

- frontend public root -> `http://127.0.0.1:18030`
- same-site `/api` -> `http://127.0.0.1:18031`

Do not change the compose file, compose project, service names, or host ports
without updating this file, the compose file, the app manifests, and host Nginx
configuration together.

## Source Image Expectations

Frontend image expectations:

- built from `https://github.com/benlagrone/solar-potential-frontend`
- serves:
  - `/`
  - `/runtime-config.js`
  - `/release-history.html`
  - `/quote/<id>` via SPA fallback
- supports runtime config keys:
  - `APP_API_BASE_URL`
  - `APP_GA_MEASUREMENT_ID`
  - `APP_DEMO_MODE`
  - `APP_SECONDARY_FRONTEND_URL`
- preferred production API behavior:
  - empty `APP_API_BASE_URL` so the app uses same-origin `/api`

Backend image expectations:

- built from `https://github.com/benlagrone/solar-potential-backend`
- serves the FastAPI app on container port `8000`
- keeps these routes available:
  - `/health`
  - `/openapi.json`
  - `/docs`
  - `/api/property-preview`
  - `/api/solar-potential`
  - `/api/solar-report`
  - `/api/solar-quote`

## Runtime Env Injection

Keep server-local runtime values in `.env.solar-potential.local` beside the
fortress checkout when this stack should be active.

Frontend env values supported by fortress compose:

- `SOLARPOTENTIAL_APP_API_BASE_URL`
- `SOLARPOTENTIAL_APP_GA_MEASUREMENT_ID`
- `SOLARPOTENTIAL_APP_DEMO_MODE`
- `SOLARPOTENTIAL_APP_SECONDARY_FRONTEND_URL`

Backend env values supported by fortress compose:

- `SOLARPOTENTIAL_RUNTIME_DIR`
- `SOLARPOTENTIAL_APP_DB_PATH`
- `SOLARPOTENTIAL_GEOCODER_PROVIDER`
- `SOLARPOTENTIAL_GEOCODER_NOMINATIM_DOMAIN`
- `SOLARPOTENTIAL_NREL_API_KEY`
- `SOLARPOTENTIAL_GOOGLE_APPLICATION_CREDENTIALS`
- `SOLARPOTENTIAL_PERSONAL_INFO_SHEET_ID`
- `SOLARPOTENTIAL_BROWSER_DATA_SHEET_ID`
- `SOLARPOTENTIAL_SOLAR_DATA_SHEET_ID`
- `SOLARPOTENTIAL_HOME_ASSISTANT_API_KEY`

Recommended production defaults:

- `SOLARPOTENTIAL_RUNTIME_DIR=./runtime/solar-potential-backend`
- `SOLARPOTENTIAL_APP_DB_PATH=/app/.runtime/solar-potential.sqlite3`
- `SOLARPOTENTIAL_GEOCODER_PROVIDER=hybrid`
- `SOLARPOTENTIAL_APP_DEMO_MODE=false`

Notes:

- keep `SOLARPOTENTIAL_APP_DB_PATH` inside `/app/.runtime` unless you also
  change the matching bind mount target
- if Google Sheets export is required, the credentials file path must resolve
  inside the running container, not only on the host
- `SOLARPOTENTIAL_HOME_ASSISTANT_API_KEY` is injected into the container as
  `HOME_ASSISTANT_API_KEY`; keep it in the Fortress `prod` environment secret,
  never in the checked-in env file

## Canonical Deploy Commands

From the fortress repo root on the target host:

```bash
if [[ -f .env.solar-potential.local ]]; then
  COMPOSE=(docker compose --env-file .env.solar-potential.local -p solar-potential -f docker-compose.solar-potential.yml)
else
  COMPOSE=(docker compose -p solar-potential -f docker-compose.solar-potential.yml)
fi
```

Frontend:

```bash
SOLARPOTENTIAL_FRONTEND_IMAGE=ghcr.io/benlagrone/solar-potential-frontend:sha-<commit> \
"${COMPOSE[@]}" pull solar-potential-frontend

SOLARPOTENTIAL_FRONTEND_IMAGE=ghcr.io/benlagrone/solar-potential-frontend:sha-<commit> \
"${COMPOSE[@]}" up -d --no-deps solar-potential-frontend

"${COMPOSE[@]}" ps solar-potential-frontend
```

Backend:

```bash
SOLARPOTENTIAL_BACKEND_IMAGE=ghcr.io/benlagrone/solar-potential-api:sha-<commit> \
"${COMPOSE[@]}" pull solar-potential-backend

SOLARPOTENTIAL_BACKEND_IMAGE=ghcr.io/benlagrone/solar-potential-api:sha-<commit> \
"${COMPOSE[@]}" up -d --no-deps solar-potential-backend

"${COMPOSE[@]}" ps solar-potential-backend
```

## GitHub Actions Control Plane

Fortress workflows:

- `.github/workflows/deploy-solar-potential-frontend.yml`
- `.github/workflows/deploy-solar-potential-backend.yml`

These workflows accept either:

- manual `workflow_dispatch` in the fortress repo
- `repository_dispatch` events sent to the fortress repo from the source repos

Preferred dedicated production secrets for frontend:

- `SOLARPOTENTIAL_FRONTEND_DEPLOY_HOST`
- `SOLARPOTENTIAL_FRONTEND_DEPLOY_USER`
- `SOLARPOTENTIAL_FRONTEND_DEPLOY_ROOT`
- `SOLARPOTENTIAL_FRONTEND_DEPLOY_SSH_KEY`
- `SOLARPOTENTIAL_FRONTEND_DEPLOY_KNOWN_HOSTS`
- `SOLARPOTENTIAL_FRONTEND_GHCR_READ_TOKEN`

Preferred dedicated production secrets for backend:

- `SOLARPOTENTIAL_BACKEND_DEPLOY_HOST`
- `SOLARPOTENTIAL_BACKEND_DEPLOY_USER`
- `SOLARPOTENTIAL_BACKEND_DEPLOY_ROOT`
- `SOLARPOTENTIAL_BACKEND_DEPLOY_SSH_KEY`
- `SOLARPOTENTIAL_BACKEND_DEPLOY_KNOWN_HOSTS`
- `SOLARPOTENTIAL_BACKEND_GHCR_READ_TOKEN`
- `SOLARPOTENTIAL_HOME_ASSISTANT_API_KEY`

These workflows are the fortress-side deployment entrypoints. The source repos
own image publication and then dispatch fortress after the images exist.

Credential resolution order in the fortress workflows:

1. use the dedicated `SOLARPOTENTIAL_*` secret family when it is fully populated
2. otherwise fall back to the shared Contabo `SOLOMONIC_CLOCK_*` secret family already used by other working fortress deploy jobs

The fallback secret family is:

- `SOLOMONIC_CLOCK_DEPLOY_HOST`
- `SOLOMONIC_CLOCK_DEPLOY_USER`
- `SOLOMONIC_CLOCK_DEPLOY_ROOT`
- `SOLOMONIC_CLOCK_DEPLOY_SSH_KEY`
- `SOLOMONIC_CLOCK_DEPLOY_KNOWN_HOSTS`
- `SOLOMONIC_CLOCK_GHCR_READ_TOKEN`

If neither set resolves all required values, the workflow fails before it tries
to open SSH so the error is explicit instead of producing an empty host target.

## Source-To-Fortress Handoff

Frontend dispatch shape:

```bash
gh api repos/benlagrone/fortress-phronesis/dispatches \
  -f event_type=deploy-solar-potential-frontend \
  -F client_payload[source_sha]=<commit-sha> \
  -F client_payload[environment]=prod
```

Backend dispatch shape:

```bash
gh api repos/benlagrone/fortress-phronesis/dispatches \
  -f event_type=deploy-solar-potential-backend \
  -F client_payload[source_sha]=<commit-sha> \
  -F client_payload[environment]=prod
```

Expected payload fields:

- `source_sha`
- `environment` with `prod` for the current fortress environment

## Host Nginx

After cutover, host Nginx should proxy:

- public site root and SPA routes -> `http://127.0.0.1:18030`
- same-site `/api` routes -> `http://127.0.0.1:18031`

Keep the exact `/api` block ahead of the generic `/` block. Keep TLS
termination on host Nginx.

## Verification

Local checks on the host:

```bash
curl -I http://127.0.0.1:18030/
curl http://127.0.0.1:18030/runtime-config.js
curl -I http://127.0.0.1:18030/release-history.html
curl http://127.0.0.1:18031/health
curl http://127.0.0.1:18031/openapi.json >/dev/null
test "$(curl -sS -o /dev/null -w '%{http_code}' \
  'http://127.0.0.1:18031/api/home-assistant/snapshot?latitude=30.2672&longitude=-97.7431')" = 401
curl -H "X-API-Key: ${SOLARPOTENTIAL_HOME_ASSISTANT_API_KEY}" \
  'http://127.0.0.1:18031/api/home-assistant/snapshot?latitude=30.2672&longitude=-97.7431' >/dev/null
docker compose -p solar-potential -f docker-compose.solar-potential.yml ps
```

## Remaining Host Prerequisites

- configure `.env.solar-potential.local` on the target host
- add host Nginx rules for the chosen public hostname set
- if Google Sheets export is needed, ensure the credential file is mounted or
  otherwise made visible inside the backend container
