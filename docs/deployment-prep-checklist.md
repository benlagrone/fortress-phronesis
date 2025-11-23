# Deployment Prep Checklist (Contabo)

- Rotate secrets and stage sanitized `.env` files (root-owned, 600) for API/frontend and Keycloak; replace exposed API/DB keys.
- Clean Nginx vhosts: dedupe `server_name` for AMA; ensure `/chat` routes to FastAPI (not WordPress); plan pericopeai.com upstreams to container ports (e.g., 127.0.0.1:18000 API, 127.0.0.1:13080 FE).
- Create Docker network: `docker network create pericope_net`; connect Keycloak container: `docker network connect pericope_net auth-keycloak-1`.
- Reserve host ports: keep 80/443 for Nginx; choose unused host ports for containers (e.g., 18000/13080); stop host uvicorn for PericopeAI at cutover.
- Add compose + Dockerfiles: `docker-compose.pericope.yml` with API (uvicorn) and frontend (nginx serving build); set DB_HOST to HostGator or local if migrating later.
- Firewall/ingress: allow only SSH/80/443; bind container ports to localhost; do not expose DB ports.
- Keycloak decision: keep Docker Keycloak + kc-db; retire host Keycloak after backup; ensure Keycloak container stays on `pericope_net`.
- DB plan: if using HostGator, confirm outbound 3306 works; if migrating local, create DB/user, import data, update `.env`, keep 3306 local-only.
- Logging/health: enable log rotation (Nginx, Docker); add healthchecks in compose; use non-root users in Dockerfiles.
- Cutover steps: `docker compose -f docker-compose.pericope.yml up -d`; update Nginx upstreams to 127.0.0.1:18000/13080; reload Nginx; smoke-test `/` and `/api`.
