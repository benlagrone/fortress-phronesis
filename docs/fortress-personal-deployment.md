# Fortress Personal Deployment

This file defines the fortress-side deployment path for the personal Fortress
Phronesis app at `fortress.benjaminlagrone.com`.

The app source lives in:

- `/Users/benjaminlagrone/Documents/projects/Fortress`
- GitHub: `benlagrone/Fortress`

The deployment control-plane entrypoint lives in this repo:

- `.github/workflows/deploy-fortress-personal.yml`
- `scripts/deploy-fortress-personal-remote.sh`

The workspace deployment policy/lock remains owned by the first-level
`workspace-deployment` project, not by this PericopeAI stack.

## Runtime Contract

- VPS: Contabo `89.117.151.145`
- Server deploy root: `/root/workspace/Fortress`
- Compose project: `fortress-personal`
- Compose file: `compose.yaml`
- Env file: `.env.contabo`
- Host bind: `127.0.0.1`
- Watch UI: `127.0.0.1:15173`
- API: `127.0.0.1:18080`
- Public host: `https://fortress.benjaminlagrone.com/`
- Host Basic Auth file: `/etc/nginx/fortress-phronesis.htpasswd`

This deployment intentionally does not change the locked PericopeAI compose
project, compose file, network, ports, or environment wiring.

## GitHub Actions Control Plane

Manual dispatch:

```bash
gh workflow run deploy-fortress-personal.yml \
  --repo benlagrone/fortress-phronesis \
  -f source_ref=main \
  -f environment=prod \
  -f run_public_smoke=true
```

Repository dispatch shape:

```bash
gh api repos/benlagrone/fortress-phronesis/dispatches \
  -f event_type=deploy-fortress-personal \
  -F client_payload[source_ref]=main \
  -F client_payload[environment]=prod \
  -F client_payload[run_public_smoke]=true
```

The workflow downloads the `benlagrone/Fortress` tarball for `source_ref`,
replaces `/root/workspace/Fortress` with that source tree while preserving
`.env.contabo`, then runs the remote deployment script on the Contabo host.

## Secrets

Preferred dedicated deploy secrets:

- `FORTRESS_PERSONAL_DEPLOY_HOST`
- `FORTRESS_PERSONAL_DEPLOY_USER`
- `FORTRESS_PERSONAL_DEPLOY_SSH_KEY`
- `FORTRESS_PERSONAL_DEPLOY_KNOWN_HOSTS`
- `FORTRESS_PERSONAL_SOURCE_READ_TOKEN`
- `FORTRESS_PERSONAL_BASIC_AUTH_USER`
- `FORTRESS_PERSONAL_BASIC_AUTH_PASSWORD`

Credential fallback:

- deploy host/user/key/known-hosts fall back to the shared
  `SOLOMONIC_CLOCK_DEPLOY_*` secret family
- source token falls back to `SOLOMONIC_CLOCK_GHCR_READ_TOKEN`

If the Fortress source repo is private, at least one source token must be able
to read `benlagrone/Fortress`. If no Basic Auth password secret is configured,
the remote script preserves the existing host htpasswd file and fails only when
no htpasswd file exists.

## Nginx And TLS

The remote script owns the `fortress.benjaminlagrone.com` host Nginx route.
That route proxies to `http://127.0.0.1:15173` and requires Basic Auth.

The permanent host needs this DNS record at HostGator:

```text
A  fortress  89.117.151.145
```

When DNS resolves to the Contabo IP, the script attempts a webroot certbot
certificate for `fortress.benjaminlagrone.com`. Until then it installs a
self-signed fallback for the hostname.

## Server-Side Direct Run

For emergency use on the Contabo host after the Fortress source tree is already
present:

```bash
FORTRESS_DEPLOY_ROOT=/root/workspace/Fortress \
FORTRESS_COMPOSE_PROJECT=fortress-personal \
FORTRESS_REMOTE_HOSTNAME=fortress.benjaminlagrone.com \
bash /tmp/deploy-fortress-personal-remote.sh
```

Prefer the GitHub Actions workflow for normal deployments so the deploy remains
auditable from the fortress-phronesis control plane.

## Verification

Server-local checks:

```bash
curl -fsS http://127.0.0.1:18080/healthz
curl -fsSI http://127.0.0.1:15173/
curl -fsS http://127.0.0.1:15173/api/healthz
docker compose -p fortress-personal --env-file /root/workspace/Fortress/.env.contabo -f /root/workspace/Fortress/compose.yaml ps
```

Public checks with Basic Auth:

```bash
curl -kfsS --resolve fortress.benjaminlagrone.com:443:89.117.151.145 \
  -u "$FORTRESS_BASIC_AUTH_USER:$FORTRESS_BASIC_AUTH_PASSWORD" \
  https://fortress.benjaminlagrone.com/api/healthz
```
