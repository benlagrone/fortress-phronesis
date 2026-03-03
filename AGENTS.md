# Immutable Deployment Contract (PericopeAI)

These rules are mandatory for this repo unless the user explicitly asks to change them with exact replacement values.

## Do Not Change
- Deployment method:
  - Use `docker compose -p fortress-phronesis -f docker-compose.pericope.yml ...`
- Compose project name:
  - `fortress-phronesis`
- Compose file:
  - `docker-compose.pericope.yml`
- Network name:
  - `fortress-phronesis-net`
- Host ports:
  - MySQL `3307`
  - API `18000`
  - Frontend `13080`
- Environment wiring and profiles used by the PericopeAI stack.

## Change Control
- Any change to method, ports, environments, compose project, or compose file requires:
  - explicit user request in the same thread
  - exact before/after values
  - matching updates to docs and smoke checks in the same change

## Enforcement
- Keep `scripts/verify-pericope-deploy-lock.sh` passing.
