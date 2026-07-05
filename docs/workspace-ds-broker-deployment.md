# Workspace DS Broker Deployment Contract

This file defines the Fortress-managed container contract for the workspace
DS/API broker.

The broker is private infrastructure. It is not a public internet service. It
must stay behind `fortress.local`, `fortress.lan`, loopback, or another
explicitly private route unless the user asks for a public deployment in the
same thread.

## Runtime Contract

Service:

- Compose file: `docker-compose.workspace-ds-broker.yml`
- Compose project: `workspace-ds-broker`
- Service: `workspace-ds-broker`
- Container: `workspace-ds-broker`
- Image: `workspace-ds-broker:local` by default
- Container port: `18100`
- Host bind: `127.0.0.1:18100`
- Health: `GET /healthz`

Source/build context:

- default compose build context: `../../.workspace`
- Dockerfile: `.workspace/ds_broker/Dockerfile`
- shared code: `.workspace/ds_broker/`
- HTTP entrypoint: `.workspace/bin/ds_api_proxy`

The image copies the workspace registry, metadata catalog, and all-project DS
plan docs into `/workspace/.workspace`. Rebuild the image after regenerating
the public dataset catalog or DS plan docs.

## Fortress Routes

Required private routes:

- `http://fortress.local/ds-broker/` -> `http://127.0.0.1:18100/`
- `http://fortress.lan/ds-broker/` -> `http://127.0.0.1:18100/` on the LAN host

Do not replace the base `fortress.local` or `fortress.lan` control planes. The
broker should be mounted as a subpath or service alias.

Optional service aliases, if the local/LAN routing layer supports them:

- `http://ds-broker.fortress.local/`
- `http://ds-broker.fortress.lan/`

Route owners:

- local aliases: `fortress-lan/scripts/fortress_alias_proxy.py`
- local alias installation/cert SANs:
  `fortress-lan/scripts/install_fortress_aliases.sh`
- LAN control plane proxy: `fortress-lan/app/main.py`
- LAN discovery metadata: `fortress-lan/app/service_discovery.py`

## Canonical Commands

From the fortress control-plane repo root:

```bash
docker compose \
  -p workspace-ds-broker \
  -f docker-compose.workspace-ds-broker.yml \
  up -d --build
```

On the Fortress LAN host, use the targeted LAN deploy wrapper from the
`fortress-lan` deploy root:

```bash
bash scripts/deploy-fortress-lan.sh --service workspace-ds-broker
```

The LAN wrapper must only build/restart the `workspace-ds-broker` compose
project and must not restart the base Fortress LAN control plane or unrelated
optional services.

Check status:

```bash
docker compose \
  -p workspace-ds-broker \
  -f docker-compose.workspace-ds-broker.yml \
  ps
```

Smoke:

```bash
curl -s http://127.0.0.1:18100/healthz
curl -s 'http://127.0.0.1:18100/v1/sources?limit=5'
curl -s 'http://127.0.0.1:18100/v1/search?q=solar&project=solar-potential&limit=3'
```

Stop:

```bash
docker compose \
  -p workspace-ds-broker \
  -f docker-compose.workspace-ds-broker.yml \
  down
```

## Environment

Supported runtime variables:

- `WORKSPACE_META_CONTEXT`: compose build context for `.workspace`; defaults to
  `../../.workspace` relative to the fortress repo root.
- `WORKSPACE_DS_BROKER_IMAGE`: image tag; defaults to
  `workspace-ds-broker:local`.
- `WORKSPACE_DS_BROKER_HOST_PORT`: host loopback port; defaults to `18100`.
- `WORKSPACE_ROOT`: container workspace root; defaults to `/workspace` in the
  image.
- `DS_BROKER_HOST`: container bind host; defaults to `0.0.0.0` in compose.
- `DS_BROKER_PORT`: container bind port; defaults to `18100` in compose.

## Deployment Boundaries

- No public DNS, public nginx, TLS, or GHCR release path is active from this
  contract.
- No secrets are required for the current read-only catalog-backed broker.
- No private connector payloads should be cached or logged by this service.
- The service currently serves a build-time catalog snapshot; live catalog
  refresh is a later broker capability.
