# LeCrown Development Runway

Authority: `workspace-deployment/locks/lecrown-development.yaml`.
This is an isolated Development release, not the Properties compatibility workflow.

## Locked Target

- Host: Contabo `89.117.151.145`, root via the approved Fortress SSH connection.
- Root: `/root/workspace/fortress-phronesis/ops/lecrown-development`.
- Compose project: `lecrown-development`; network: `lecrown-development-net`.
- Loopback frontend/API: `13095` / `18045`.
- Public app/API: `app.lecrowndevelopment.com` / `api.lecrowndevelopment.com`.
- Dedicated volume: `lecrown_development_data`; no Properties database is copied.
- Previous shared upstreams: `13084` / `18035`, retained for Properties without restart.
- Candidate file: `/app/data/procurement-candidates.json`, private and persistent.

The owner runner builds private SHA-tagged images from a committed source archive.
It does not require GHCR credential changes or switch GitHub accounts. Only the
backend and frontend Git trees are archived; ignored environments and data are excluded.
Runtime secrets are selected by name from approved local files, sent over SSH stdin,
stored mode 0600 in the dedicated runtime, and never printed. Existing settings are
not overwritten. Credential rotation requires a separate authorized operation.

## Release

Use the Development Python environment (includes python-dotenv):

```sh
/Users/benjaminlagrone/Documents/projects/metroLecrown/platform/backend/.venv/bin/python \
  ops/lecrown-development/deploy.py --source-sha FULL_COMMIT
```

After scope approval, add `--apply` and supply `--app-env`, `--crm-env`, and `--ssh-env`
with the explicitly authorized Development, EspoCRM, and Fortress connection files.
Do not print their contents. Run workspace lock/runway validation before applying.

The installer checks unclaimed loopback ports, volume/network ownership, image revision
labels, backend health, admin authentication, and inbox capability before changing
only the two Development upstreams. TLS and other vhosts are preserved. It compares
Properties container IDs and nginx hashes before and after cutover, and checks its
public health. Failure restores the two Development vhosts and prior Development
release, or stops only the new project on its first release, without removing data.

## Verification

- Public Development app, same-origin `/api/healthz`, and API health return successfully.
- Authenticated `/contracts/capabilities` reports `candidate_inbox_enabled: true`.
- Collector runs bounded batches every 900 seconds, with 10 Bonfire attempts spaced
  at least six seconds apart; it cannot overlap a manual batch or create CRM records.
- Authenticated `/contracts/candidates/export.json` contains actual source-backed
  candidates. Promotion tests use mocks; do not create test Opportunities in live CRM.
- Preserve Properties container IDs, vhosts, database, credentials, and public health.
- Record source SHA, archive digest, backup path, and release timestamp in `release.json`.

## Rollback

Use the same runner with `--rollback EXACT_BACKUP_DIRECTORY --apply --ssh-env FILE`.
The backup path must belong to this Development deployment. The initial-split rollback
restores Development's old shared upstreams and stops only `lecrown-development`, keeping
its data volume. Later rollbacks restore the prior Development image pins and compose
definition. Properties is never stopped, rebuilt, migrated, or reconfigured.
