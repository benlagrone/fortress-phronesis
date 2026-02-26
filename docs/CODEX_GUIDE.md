# Codex Guide: fortress-phronesis

## Purpose
This repo is a control-plane for deploying and operating PericopeAI and related services
(AskMortgageAuthority WordPress, chat, calculators) across a hybrid setup (Contabo VPS
plus HostGator shared hosting). It contains Docker Compose stacks, deployment scripts,
and system handback documentation for production operations.

## What lives here
- Docker Compose definitions for:
  - PericopeAI full stack (API, frontend, MySQL, corpus)
  - Corpus-only stack
  - AMA calculators
  - Containerized WordPress (optional)
- Scripts for deploy, update, and WordPress content pulls.
- Operational docs covering deployment, architecture diagrams, and hardening.

## Key components and external repos
This repo expects service code in sibling paths on the host:
- PericopeAI API: `/root/workspace/AugustineService`
- PericopeAI Frontend: `/root/workspace/AugustineFE`
- Corpus service: `/root/workspace/AugustineCorpus`
- AMA calculators: `/root/workspace/calculator.askmortgageauthority.com`
- AMA WordPress: `/root/workspace/askmortgageauthority.com`

## Services and ports (host mappings)
PericopeAI stack (`docker-compose.pericope.yml`):
- MySQL: host `3307` -> container 3306
- API: host 18000 -> container 8080
- Frontend: host 3000 -> container 80
- Corpus: internal 8001 (no host mapping)

Port mappings are fixed:
- MySQL `3307`
- API `18000`
- Frontend `3000`

## Immutable deployment lock
- Canonical command form:
  - `docker compose -p fortress-phronesis -f docker-compose.pericope.yml ...`
- Run lock check before deploy:
  - `bash scripts/verify-pericope-deploy-lock.sh`
- Do not change project name, compose file, network name, or PericopeAI host ports without explicit user approval and matching doc updates.

Calculators (`docker-compose.calculators.yml`):
- host 18010 -> container 8000

WordPress (optional container stack, `docker-compose.wordpress.yml`):
- host 18020 -> nginx container 80 (php-fpm in wordpress container)

## Primary workflows

PericopeAI full stack bring-up:
- `docker compose -p fortress-phronesis -f docker-compose.pericope.yml up -d --build`
- Verify:
  - `curl -I http://127.0.0.1:18000/api/docs`
  - `curl -I http://127.0.0.1:3000`

Corpus-only:
- `docker compose -f docker-compose.corpus.yml up -d --build augustine-corpus-live`
- Optional index run:
  - `docker compose -f docker-compose.corpus.yml --profile index run --rm pericopeai-indexer`

PericopeAI updates:
- `docker compose -p fortress-phronesis -f docker-compose.pericope.yml up -d --build pericopeai-api pericopeai-frontend augustine-corpus-live`

Calculators deploy:
- `bash scripts/deploy-calculators.sh`

WordPress content pulls (requires `scripts/.env`):
- `bash scripts/pull-wp-config.sh`
- `bash scripts/pull-wp-content.sh`

## Nginx routing expectations (host)
The host Nginx terminates TLS and proxies to container ports:
- `location /api` -> `127.0.0.1:18000`
- `location /` -> `127.0.0.1:3000`

AMA chat and WordPress routing should avoid conflicting vhosts
and duplicate `server_name` blocks. See `docs/system-handbook.md`.

## Scripts overview
- `scripts/deploy-pericopeai-prod.sh`: deploy a standalone AugustineService stack (legacy path).
- `scripts/deploy-calculators.sh`: build/run calculators container or use its compose.
- `scripts/pull-wp-config.sh` and `scripts/pull-wp-content.sh`: sync WordPress files from remote host.
- `scripts/update-nginx-*.sh`: helper templates for Nginx updates (review before use).

## Documentation map
- `docs/system-handbook.md`: current verified state, hosts, services, and conflicts.
- `docs/pericopeai-deployment.md`: repeatable PericopeAI deployment steps.
- `docs/container-management.md`: operations for API/FE/DB, logs, and checks.
- `docs/containerization-plan.md`: phased plan for containerization and cutover.
- `docs/hardening-plan.md`: security, auth, and network hardening checklist.
- `docs/handback.md`: full operational handback and DNS map.
- `docs/*.mmd`: Mermaid architecture diagrams and templates.
- `docs/structured-prompt-*.md`: prompt templates for generating architecture diagrams.

## Notes for Codex
- This repo does not contain application source; it orchestrates external repos.
- Be careful with production secrets. .env files live outside this repo and should be
  rotated or sanitized before sharing.
- If you need to modify Compose paths, update compose files and documentation together.
