# Energy Data Explorer Deployment Contract

This file defines the fortress-side deployment contract for Energy Data Explorer
when it is served from the Contabo container host.

It does not claim that DNS or Nginx cutover has already happened. The current
verified hosting state in [System Handbook](system-handbook.md) remains
authoritative until the migration is executed.

## Current Intent

Energy Data Explorer is split into two deploy targets:

- frontend at `energydataexplorer.com` and `www.energydataexplorer.com`
- API at `api.energydataexplorer.com`

The source tree currently lives at:

- `/Users/benjaminlagrone/Documents/projects/energydataexplorer`

The existing source-side workflows in that tree still use SSH/rsync. This
fortress contract adds the missing image-based control-plane path so the split
frontend/API runtime can be deployed the same way as the other fortress-managed
sites once the source repo publishes matching GHCR images.

## Runtime Contract

Shared compose contract:

- Compose file: `docker-compose.energydataexplorer.yml`
- Compose project: `energydataexplorer`

Frontend runtime:

- Service: `energydataexplorer-frontend`
- Host bind: `127.0.0.1:13083`
- Container port: `80`
- Host Nginx upstream: `http://127.0.0.1:13083`
- Public hosts: `https://energydataexplorer.com/`, `https://www.energydataexplorer.com/`
- Image contract: `ghcr.io/benlagrone/energydataexplorer-frontend:sha-<commit>`

API runtime:

- Service: `energydataexplorer-api`
- Host bind: `127.0.0.1:18038`
- Container port: `80`
- Host Nginx upstream: `http://127.0.0.1:18038`
- Public host: `https://api.energydataexplorer.com/`
- Image contract: `ghcr.io/benlagrone/energydataexplorer-api:sha-<commit>`

Do not change the compose file, compose project, service names, or host ports
without updating this file, the compose file, the app manifests, and host Nginx
configuration together.

## Source Image Expectations

Frontend image expectations:

- built from the source tree under `frontend/`
- serves the SPA root and keeps these paths available:
  - `/`
  - `/robots.txt`
  - `/sitemap.xml`
  - `/silent-check-sso.html`
  - `/downloads/texas-operator-activity-report.md`
- uses a production API target consistent with fortress host routing
  - preferred: bundle defaults to `/api`
  - acceptable: bundle bakes `https://api.energydataexplorer.com/api`

API image expectations:

- built from the source tree under `oil-index/`
- serves the Laravel app over HTTP on container port `80`
- keeps `php` and `artisan` available in the running container so fortress can
  run `php artisan migrate --force` when requested
- keeps these routes available:
  - `/api/marketing/summary`
  - `/api/texas-companies`
  - `/api/texas-companies/{id}`

## Runtime Env Injection

The API service reads runtime values from environment variables. On the server,
keep those in a local-only `.env.energydataexplorer-api.local` file beside the
fortress checkout when the API runtime should be active.

The fortress compose file and workflow support these values:

- `EDE_APP_NAME`
- `EDE_APP_ENV`
- `EDE_APP_DEBUG`
- `EDE_APP_URL`
- `EDE_APP_KEY`
- `EDE_LOG_CHANNEL`
- `EDE_LOG_LEVEL`
- `EDE_DB_CONNECTION`
- `EDE_DB_HOST`
- `EDE_DB_PORT`
- `EDE_DB_DATABASE`
- `EDE_DB_USERNAME`
- `EDE_DB_PASSWORD`
- `EDE_DB_SOCKET`
- `EDE_MYSQL_ATTR_SSL_CA`
- `EDE_CORS_ALLOWED_ORIGINS`
- `EDE_KEYCLOAK_AUTH_ENFORCED`
- `EDE_KEYCLOAK_ISSUER`
- `EDE_KEYCLOAK_JWKS_URL`
- `EDE_KEYCLOAK_AUDIENCES`
- `EDE_KEYCLOAK_JWKS_CACHE_SECONDS`
- `EDE_KEYCLOAK_ALLOWED_CLOCK_SKEW`
- `EDE_SESSION_DRIVER`
- `EDE_SESSION_LIFETIME`
- `EDE_CACHE_STORE`
- `EDE_QUEUE_CONNECTION`

At minimum, production needs valid values for:

- `EDE_APP_KEY`
- `EDE_DB_HOST`
- `EDE_DB_DATABASE`
- `EDE_DB_USERNAME`
- `EDE_DB_PASSWORD`

## Canonical Deploy Commands

From the fortress repo root on the target host:

Frontend:

```bash
ENERGYDATAEXPLORER_FRONTEND_IMAGE=ghcr.io/benlagrone/energydataexplorer-frontend:sha-<commit> \
docker compose -p energydataexplorer -f docker-compose.energydataexplorer.yml pull energydataexplorer-frontend

ENERGYDATAEXPLORER_FRONTEND_IMAGE=ghcr.io/benlagrone/energydataexplorer-frontend:sha-<commit> \
docker compose -p energydataexplorer -f docker-compose.energydataexplorer.yml up -d energydataexplorer-frontend

docker compose -p energydataexplorer -f docker-compose.energydataexplorer.yml ps energydataexplorer-frontend
```

API:

```bash
if [[ -f .env.energydataexplorer-api.local ]]; then
  COMPOSE=(docker compose --env-file .env.energydataexplorer-api.local -p energydataexplorer -f docker-compose.energydataexplorer.yml)
else
  COMPOSE=(docker compose -p energydataexplorer -f docker-compose.energydataexplorer.yml)
fi

ENERGYDATAEXPLORER_API_IMAGE=ghcr.io/benlagrone/energydataexplorer-api:sha-<commit> \
"${COMPOSE[@]}" pull energydataexplorer-api

ENERGYDATAEXPLORER_API_IMAGE=ghcr.io/benlagrone/energydataexplorer-api:sha-<commit> \
"${COMPOSE[@]}" up -d energydataexplorer-api

"${COMPOSE[@]}" ps energydataexplorer-api

"${COMPOSE[@]}" exec -T energydataexplorer-api php artisan migrate --force
```

## GitHub Actions Control Plane

Fortress workflows:

- `.github/workflows/deploy-energydataexplorer-frontend.yml`
- `.github/workflows/deploy-energydataexplorer-api.yml`

These workflows accept either:

- manual `workflow_dispatch` in the fortress repo
- `repository_dispatch` events sent to the fortress repo from the source repo or
  another release orchestrator

Preferred dedicated production secrets for frontend:

- `ENERGYDATAEXPLORER_FRONTEND_DEPLOY_HOST`
- `ENERGYDATAEXPLORER_FRONTEND_DEPLOY_USER`
- `ENERGYDATAEXPLORER_FRONTEND_DEPLOY_ROOT`
- `ENERGYDATAEXPLORER_FRONTEND_DEPLOY_SSH_KEY`
- `ENERGYDATAEXPLORER_FRONTEND_DEPLOY_KNOWN_HOSTS`
- `ENERGYDATAEXPLORER_FRONTEND_GHCR_READ_TOKEN`

Preferred dedicated production secrets for API:

- `ENERGYDATAEXPLORER_API_DEPLOY_HOST`
- `ENERGYDATAEXPLORER_API_DEPLOY_USER`
- `ENERGYDATAEXPLORER_API_DEPLOY_ROOT`
- `ENERGYDATAEXPLORER_API_DEPLOY_SSH_KEY`
- `ENERGYDATAEXPLORER_API_DEPLOY_KNOWN_HOSTS`
- `ENERGYDATAEXPLORER_API_GHCR_READ_TOKEN`

Credential resolution order in the fortress workflows:

1. use the dedicated `ENERGYDATAEXPLORER_*` secret family when it is fully populated
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

These workflows are manual control-plane entrypoints now. The source repo still
needs matching GHCR publish steps before releases become fully automatic again.

## Source-To-Fortress Handoff

Once the source repo publishes the matching GHCR image tags, it can trigger the
fortress control plane without a human opening the Actions UI.

Frontend dispatch shape:

```bash
gh api repos/benlagrone/fortress-phronesis/dispatches \
  -f event_type=deploy-energydataexplorer-frontend \
  -F client_payload[source_sha]=<commit-sha> \
  -F client_payload[environment]=prod \
  -F client_payload[run_public_smoke]=false
```

API dispatch shape:

```bash
gh api repos/benlagrone/fortress-phronesis/dispatches \
  -f event_type=deploy-energydataexplorer-api \
  -F client_payload[source_sha]=<commit-sha> \
  -F client_payload[environment]=prod \
  -F client_payload[run_migrations]=true \
  -F client_payload[run_public_smoke]=false
```

Expected payload fields:

- `source_sha`
- `environment` with `prod` for the current fortress environment
- `run_public_smoke` for either workflow
- `run_migrations` for the API workflow

This keeps deploy credentials and server targeting in the fortress repo while
letting the source repo own image publication.

## Host Nginx

After cutover, host Nginx should proxy:

- `energydataexplorer.com` and `www.energydataexplorer.com`
  - `location /api` -> `http://127.0.0.1:18038`
  - `location /` -> `http://127.0.0.1:13083`
- `api.energydataexplorer.com`
  - all traffic -> `http://127.0.0.1:18038`

If the frontend bundle uses `/api`, keep the exact `/api` block ahead of the
generic `/` block on the apex site config.

Keep TLS termination on host Nginx.

## Verification

Local checks on the host:

```bash
curl -I http://127.0.0.1:13083/
curl http://127.0.0.1:13083/robots.txt
curl http://127.0.0.1:13083/sitemap.xml
curl http://127.0.0.1:18038/api/marketing/summary >/dev/null
curl http://127.0.0.1:18038/api/texas-companies >/dev/null
docker compose -p energydataexplorer -f docker-compose.energydataexplorer.yml ps
```

Public checks after DNS and Nginx cutover:

```bash
curl -I https://energydataexplorer.com/
curl -I https://www.energydataexplorer.com/
curl https://energydataexplorer.com/robots.txt
curl https://energydataexplorer.com/sitemap.xml
curl https://api.energydataexplorer.com/api/marketing/summary >/dev/null
curl https://api.energydataexplorer.com/api/texas-companies >/dev/null
```

## Rollback

Rollback means redeploying a prior green image SHA without rebuilding on the
server:

```bash
ENERGYDATAEXPLORER_FRONTEND_IMAGE=ghcr.io/benlagrone/energydataexplorer-frontend:sha-<old-sha> \
docker compose -p energydataexplorer -f docker-compose.energydataexplorer.yml up -d energydataexplorer-frontend

if [[ -f .env.energydataexplorer-api.local ]]; then
  COMPOSE=(docker compose --env-file .env.energydataexplorer-api.local -p energydataexplorer -f docker-compose.energydataexplorer.yml)
else
  COMPOSE=(docker compose -p energydataexplorer -f docker-compose.energydataexplorer.yml)
fi

ENERGYDATAEXPLORER_API_IMAGE=ghcr.io/benlagrone/energydataexplorer-api:sha-<old-sha> \
"${COMPOSE[@]}" up -d energydataexplorer-api
```
