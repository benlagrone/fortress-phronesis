# Fortress Legal Technologies Deployment

This document is the production implementation contract for `fortresslegaltech.com`. The source application lives in `/Users/benjaminlagrone/Documents/projects/fortresslegaltech.com`; operational Compose, nginx, TLS, and host routing remain owned by Fortress Phronesis.

## Locked Runtime

- Deployment target: Contabo `vmi2669159`
- Stack root: `/root/workspace/fortress-phronesis`
- Compose file: `docker-compose.fortresslegaltech.yml`
- Compose project: `fortresslegaltech`
- Service: `fortresslegaltech`
- Image: `ghcr.io/benlagrone/fortresslegaltech:sha-<commit>`
- Host bind: `127.0.0.1:18042`
- Public hosts: `https://fortresslegaltech.com/` and `https://www.fortresslegaltech.com/`

The application container is never exposed on a public host interface. Host nginx is the only public entry point.

## Current Gate

The runtime contract is prepared but must not be represented as deployed until all of these are true:

1. `benlagrone/fortresslegaltech.com` exists and the source commit is pushed.
2. The matching immutable GHCR image exists.
3. The Phronesis production checkout is clean and synchronized to the deployment commit.
4. Namecheap DNS points the apex and `www` records to the authorized public host.
5. Local health, nginx bootstrap, ACME issuance, TLS routing, and public acceptance checks pass.

## Deploy

Run from the synchronized Phronesis stack root:

```bash
FORTRESSLEGALTECH_IMAGE=ghcr.io/benlagrone/fortresslegaltech:sha-<commit> \
docker compose -p fortresslegaltech -f docker-compose.fortresslegaltech.yml pull fortresslegaltech

FORTRESSLEGALTECH_IMAGE=ghcr.io/benlagrone/fortresslegaltech:sha-<commit> \
docker compose -p fortresslegaltech -f docker-compose.fortresslegaltech.yml up -d fortresslegaltech

docker compose -p fortresslegaltech -f docker-compose.fortresslegaltech.yml ps
curl -fsS http://127.0.0.1:18042/healthz
curl -fsS http://127.0.0.1:18042/expunction >/dev/null
```

Do not set `FORTRESSLEGALTECH_LEGAL_API_BASE_URL` until an authenticated server-to-server route is approved. The public app remains useful with that optional capability unconfigured and does not expose personal Fortress data.

## DNS And TLS

1. Install `deploy/nginx/fortresslegaltech.com.bootstrap.conf` only after the container health checks pass.
2. Point Namecheap apex `A` and `www` records at the authorized public host.
3. Verify public DNS from an external resolver.
4. Issue one certificate covering `fortresslegaltech.com` and `www.fortresslegaltech.com`.
5. Replace the bootstrap vhost with `deploy/nginx/fortresslegaltech.com.conf`.
6. Run `nginx -t` before every reload.

## Acceptance

```bash
curl -fsS https://fortresslegaltech.com/healthz
curl -fsS https://fortresslegaltech.com/expunction >/dev/null
curl -fsS https://fortresslegaltech.com/api/v1/workflows/expunction >/dev/null
curl -fsSI https://www.fortresslegaltech.com/ | grep -i '^location: https://fortresslegaltech.com/'
```

Browser acceptance must verify desktop and mobile layouts, the Civil/Expunction submenu, and a successful non-persistent intake preview.

## Rollback

Set `FORTRESSLEGALTECH_IMAGE` to the prior immutable `sha-<commit>` image and rerun the same Compose `up -d` command. Verify loopback health before leaving nginx enabled.

