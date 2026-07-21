# Workspace-Level Deployment Runway

This repo is also the current implementation surface for the workspace-level deployment runway.
Before any deploy, release, rollback, production, staging,
Contabo, VPS, GHCR, Docker Compose, nginx, TLS, domain, public-port, or runtime
environment work, read and follow:

- `/Users/benjaminlagrone/Documents/projects/.workspace/deployment-policy.md`
- `/Users/benjaminlagrone/Documents/projects/workspace-deployment/policy.md`
- `/Users/benjaminlagrone/Documents/projects/workspace-deployment/locks/pericopeai.yaml`
- `/Users/benjaminlagrone/Documents/projects/AGENTS.md`
- this file

Do not create or endorse a competing deployment path unless the user explicitly
asks to replace the workspace deployment runway in the same thread.

# Shared Capability Boundary

Shared workspace capabilities follow this mandatory shape:

```text
client or browser -> app same-origin route -> owning capability service -> provider adapters
```

For voice, PericopeAI, TrueVineOS/Solomonic Clock, and Fortress Personal are
consumers. Production voice must route through `fortress-lan:voice-gateway`.
Direct VibeVoice, Azure Voice, OpenAI Audio, browser speech synthesis, or local
STT/TTS provider routes are diagnostic bypasses only unless the workspace lock
explicitly changes in the same task.

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
  - Solomonic Clock `8086`
- Environment wiring and profiles used by the PericopeAI stack.

## Change Control
- Any change to method, ports, environments, compose project, or compose file requires:
  - explicit user request in the same thread
  - exact before/after values
  - matching updates to docs and smoke checks in the same change

## Enforcement
- Keep `scripts/verify-pericope-deploy-lock.sh` passing.
