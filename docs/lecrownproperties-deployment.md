# LeCrown Properties Deployment Contract

This file defines the fortress-side deployment contract for `lecrownproperties.com`
when it is served from the Contabo container host.

It mirrors the existing runtime contract in the sibling source repo and moves the
release path to immutable GHCR images pulled by `fortress-phronesis`.

## Runtime Contract

- Compose file: `docker-compose.lecrownproperties.yml`
- Compose project: `lecrownproperties`
- Service: `lecrown-properties-site`
- Host bind: `127.0.0.1:18033`
- Container port: `8080`
- Host Nginx upstream: `http://127.0.0.1:18033`
- Public host: `https://lecrownproperties.com/`
- Optional redirect host: `https://www.lecrownproperties.com/`
- Image contract: `ghcr.io/benlagrone/lecrownproperties-site:sha-<commit>`

Do not change the project name, service name, or host port without updating
this file, the compose file, and the host Nginx configuration together.

## Source Image Expectations

The source content currently exists in the sibling repo:

- `/Users/benjaminlagrone/Documents/projects/real-estate/lecrownproperties`

The published image is expected to keep these paths available:

- `/`
- `/contact?lang=zh`
- `/data/site.en.json`
- `/health`

When GridScope runtime settings are present, the same container also serves:

- `POST /api/gridscope/evaluate`
- `GET /api/gridscope/markets`

## Runtime Env Injection

The container reads these values from environment variables when they are
present:

- `GRIDSCOPE_EXTERNAL_API_URL`
- `GRIDSCOPE_EXTERNAL_API_KEY`
- `GRIDSCOPE_EXTERNAL_API_AUTH_MODE`
- `GRIDSCOPE_EXTERNAL_API_HEADER_NAME`
- `GRIDSCOPE_EXTERNAL_API_TIMEOUT_MS`
- `GRIDSCOPE_EXTERNAL_API_CACHE_TTL_SECONDS`

Keep those values in a server-local env file outside the synced fortress
checkout when the GridScope proxy should be active. Do not place the file inside
`DEPLOY_ROOT`, because the sync contract requires a clean checkout. The fortress
workflow can also materialize this env file from GitHub Actions secrets during
deploy.

## Canonical Deploy Commands

From the fortress repo root on the target host:

```bash
GRIDSCOPE_ENV_FILE=/opt/lecrownproperties/env/gridscope.prod.env

if [[ -f "${GRIDSCOPE_ENV_FILE}" ]]; then
  COMPOSE=(docker compose --env-file "${GRIDSCOPE_ENV_FILE}" -p lecrownproperties -f docker-compose.lecrownproperties.yml)
else
  COMPOSE=(docker compose -p lecrownproperties -f docker-compose.lecrownproperties.yml)
fi

LECROWNPROPERTIES_IMAGE=ghcr.io/benlagrone/lecrownproperties-site:sha-<commit> \
"${COMPOSE[@]}" pull lecrown-properties-site

LECROWNPROPERTIES_IMAGE=ghcr.io/benlagrone/lecrownproperties-site:sha-<commit> \
"${COMPOSE[@]}" up -d lecrown-properties-site

"${COMPOSE[@]}" ps lecrown-properties-site
```

## GitHub Actions Control Plane

Fortress workflow:

- `.github/workflows/deploy-lecrownproperties.yml`

Expected production secrets:

- `LECROWNPROPERTIES_DEPLOY_HOST`
- `LECROWNPROPERTIES_DEPLOY_USER`
- `LECROWNPROPERTIES_DEPLOY_ROOT`
- `LECROWNPROPERTIES_DEPLOY_SSH_KEY`
- `LECROWNPROPERTIES_DEPLOY_KNOWN_HOSTS`
- `LECROWNPROPERTIES_GHCR_READ_TOKEN`
- `LECROWNPROPERTIES_GRIDSCOPE_EXTERNAL_API_URL`
- `LECROWNPROPERTIES_GRIDSCOPE_EXTERNAL_API_KEY`
- `LECROWNPROPERTIES_GRIDSCOPE_EXTERNAL_API_AUTH_MODE`
- `LECROWNPROPERTIES_GRIDSCOPE_EXTERNAL_API_HEADER_NAME`
- `LECROWNPROPERTIES_GRIDSCOPE_EXTERNAL_API_TIMEOUT_MS`
- `LECROWNPROPERTIES_GRIDSCOPE_EXTERNAL_API_CACHE_TTL_SECONDS`
- `LECROWNPROPERTIES_KEYCLOAK_BASE_URL` (optional, default `https://auth.pericopeai.com`)
- `LECROWNPROPERTIES_KEYCLOAK_REALM` (optional, default `lecrown-portal`)
- `LECROWNPROPERTIES_KEYCLOAK_CLIENT_ID` (optional, default `lecrown-portal-web`)
- `LECROWNPROPERTIES_KEYCLOAK_CLIENT_SECRET` (optional)
- `LECROWNPROPERTIES_KEYCLOAK_REDIRECT_URI` (optional, default inferred as `https://lecrownproperties.com/auth/callback`)
- `LECROWNPROPERTIES_KEYCLOAK_PUBLIC_ORIGIN` (optional, default `https://lecrownproperties.com`)
- `LECROWNPROPERTIES_KEYCLOAK_ALLOWED_ROLES` (optional comma-separated role allowlist)
- `LECROWNPROPERTIES_KEYCLOAK_AUTH_SCOPE` (optional, default `openid profile email`)

The source repo dispatches this workflow after publishing
`ghcr.io/benlagrone/lecrownproperties-site:sha-<commit>`.

## Host Nginx

Host Nginx should proxy the public site to:

- `http://127.0.0.1:18033`

If `www.lecrownproperties.com` is desired, handle it in host Nginx as a redirect
or as a second `server_name` on the same upstream. Keep TLS termination on host
Nginx.

## Verification

Local checks on the host:

```bash
curl -fsS http://127.0.0.1:18033/health
curl -fsS http://127.0.0.1:18033/api/gridscope/markets
curl -fsS http://127.0.0.1:18033/ >/dev/null
curl -fsS "http://127.0.0.1:18033/contact?lang=zh" >/dev/null
curl -fsS http://127.0.0.1:18033/data/site.en.json >/dev/null
docker compose -p lecrownproperties -f docker-compose.lecrownproperties.yml ps
```

Public checks after DNS and Nginx cutover:

```bash
curl -fsS https://lecrownproperties.com/ >/dev/null
curl -fsS "https://lecrownproperties.com/contact?lang=zh" >/dev/null
curl -fsS https://lecrownproperties.com/data/site.en.json >/dev/null
curl -fsS https://www.lecrownproperties.com/ >/dev/null
```

## Rollback

Rollback means redeploying a prior green image SHA without rebuilding on the
server:

```bash
GRIDSCOPE_ENV_FILE=/opt/lecrownproperties/env/gridscope.prod.env

if [[ -f "${GRIDSCOPE_ENV_FILE}" ]]; then
  COMPOSE=(docker compose --env-file "${GRIDSCOPE_ENV_FILE}" -p lecrownproperties -f docker-compose.lecrownproperties.yml)
else
  COMPOSE=(docker compose -p lecrownproperties -f docker-compose.lecrownproperties.yml)
fi

LECROWNPROPERTIES_IMAGE=ghcr.io/benlagrone/lecrownproperties-site:sha-<old-sha> \
"${COMPOSE[@]}" up -d lecrown-properties-site
```
