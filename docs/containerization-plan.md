# Containerization Plan (Phased)

## Phase 1: PericopeAI Frontend + API (target now)
- Compose stack:
  - pericopeai-api (uvicorn), pericopeai-frontend (nginx serving build).
  - Network: `pericope_net`.
  - Keycloak container (`auth-keycloak-1`) attached to `pericope_net`; kc-db stays as-is.
- Code pull/contexts:
  - API build context: `/var/www/pericopeai.com/AugustineService/` (contains main.py, requirements.txt, .env).
  - Frontend build context: `/var/www/pericopeai/` (React app to build then serve via nginx).
- Host mappings:
  - API container port 8000 → host 18000.
  - FE container port 80 → host 13080.
  - Nginx host upstreams: `/api` → 127.0.0.1:18000; `/` → 127.0.0.1:13080 (after cutover).
- DB:
  - Keep HostGator MySQL for now (`gator4416.hostgator.com`, DB `cwrihote_chatbook`).
  - Option later: migrate to local DB; would require schema/data import and env updates.
- Actions:
  - Rotate secrets; sanitize `.env` for containers.
  - Build/run: `docker compose -f docker-compose.pericope.yml up -d`.
  - Connect Keycloak to network: `docker network connect pericope_net auth-keycloak-1`.
  - Update host Nginx upstreams; reload; stop host uvicorn.

## Phase 2: AMA Chat API
- Containerize FastAPI Chat service.
- Network: join `pericope_net`.
- Host mapping: container 8000 → host 19001 (example).
- Nginx host: `/chat` (or chat.askmortgageauthority.com) → 127.0.0.1:19001.
- Code pull/context: `/var/www/chat-api/` (app/main.py, .env).
- DB:
  - If staying HostGator, set DB host accordingly; else plan migration to local DB.
- Actions:
  - Compose service added; healthcheck; non-root user.
  - Fix AMA vhost conflict so chat is not overridden by WordPress.

## Phase 3: Keycloak Consolidation
- Choose Docker Keycloak + kc-db as source of truth; retire host Keycloak.
- Backup realms; import into the chosen instance.
- Keep Keycloak on `pericope_net`; proxy via host Nginx to localhost-mapped port.

## Phase 4: WordPress + Apache/DB
- Option A: Keep WordPress on host Apache 8080 behind Nginx; just clean vhosts.
- Option B: Containerize WordPress + php-fpm + DB (with persistent volumes); move Nginx host to reverse proxy only.
- Code/content location if containerized: `/var/www/askmortgageauthority/` mapped to a volume for wp-content/uploads; DB volume for the WordPress DB.
- DB: decide whether to keep local MariaDB or move to containerized DB; ensure backups/restore.

## Phase 5: Remaining Services (CRM/Calculators)
- If migrating from HostGator, plan Laravel/CRM container and DB migration.
- Otherwise, document external dependency and outbound connectivity requirements.

## Cross-Cutting Hardening
- Secrets: rotate exposed keys; store envs root-owned (600) or in secret manager.
- Networking: public only 80/443 (SSH as needed); bind container ports to localhost; private Docker network for app-to-app.
- Logging/health: log rotation (Nginx, Docker); healthchecks in compose; non-root users in Dockerfiles; pin base images.
- Backups: schedule DB/realm backups; test restores.

## Cutover Pattern (per service)
1) Build images.
2) `docker compose up -d`.
3) Update Nginx upstreams to localhost-mapped ports.
4) Reload Nginx; smoke test.
5) Stop old host process to avoid duplicate bindings.
