# PericopeAI Shared Assets Deployment

This deploy path serves shared SVG and static assets from the sibling `pericopeai-assets` repo through Fortress on `assets.pericopeai.com`.

## Current state

- GitHub repo: `benlagrone/pericopeai-assets`
- Asset repo commit: `cd71aa4` (`Initial shared asset library`)
- Publish workflow: succeeded on push to `main`
- Image tags published: `ghcr.io/benlagrone/pericopeai-assets:latest` and `ghcr.io/benlagrone/pericopeai-assets:sha-cd71aa44e0d5391587164663e7dbbcea2cee7029`
- Public DNS for `assets.pericopeai.com` is not live yet

## What Fortress owns

- Compose service: `pericopeai-assets` on `127.0.0.1:13084`
- Deployment workflow: `.github/workflows/deploy-pericopeai-assets.yml`
- App manifest: `deploy/apps/pericopeai-assets.yaml`
- Prod registry entry: `deploy/environments/prod.yaml` (currently `enabled: false`)
- Repo bootstrap helper: `scripts/create-pericopeai-assets-remote.sh`
- Nginx vhost helper: `scripts/update-nginx-pericopeai-assets.sh`

## Deploy now

Trigger the workflow with:

- `source_sha=cd71aa44e0d5391587164663e7dbbcea2cee7029`
- `environment=prod`
- `run_public_smoke=false`

The workflow reuses the existing `SOLOMONIC_CLOCK_*` deploy secrets so it can SSH to the same Fortress host and pull from GHCR.

## Remaining public cutover work

1. Publish DNS for `assets.pericopeai.com`.
2. Provision the `assets.pericopeai.com` certificate on the host.
3. Install or update the nginx vhost with `scripts/update-nginx-pericopeai-assets.sh`.
4. Re-run the deploy workflow with `run_public_smoke=true`.
5. Flip `pericopeai-assets.enabled` to `true` in `deploy/environments/prod.yaml` after public checks pass.
