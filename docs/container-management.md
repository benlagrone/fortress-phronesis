# Container Management (PericopeAI)

This document governs the shared `fortress-phronesis` stack. It is not the default local standalone development workflow on macOS.

For local standalone containers, use:
- [Local Pericope Stack Runbook](local-pericope-stack-runbook.md)

Repo root: `/root/workspace/fortress-phronesis`
Compose file: `docker-compose.pericope.yml`
Services: `mysql` (host port `3307` → container 3306, volume `mysql_data`), `augustine-corpus-live` (internal port `8001`), `pericopeai-api` (host port `18000` → container `8080`), `solomonic-clock` (host port `8086` → container `8080`), `pericopeai-frontend` (host port `13080` → container `80`)
Network: external `fortress-phronesis-net`

Deployment lock check:
```bash
bash scripts/verify-pericope-deploy-lock.sh
```

## Update & Rebuild
- Backend only (after pulling AugustineService code):
  ```bash
  docker compose -p fortress-phronesis -f docker-compose.pericope.yml up -d --build pericopeai-api
  ```
- Frontend only (after pulling AugustineFE code):
  ```bash
  docker compose -p fortress-phronesis -f docker-compose.pericope.yml up -d --build pericopeai-frontend
  ```
- Solomonic Clock only (after pulling Solomonic_Seals code):
  ```bash
  docker compose -p fortress-phronesis -f docker-compose.pericope.yml up -d --build solomonic-clock
  ```
- Restart without rebuild (config-only):
  ```bash
  docker compose -p fortress-phronesis -f docker-compose.pericope.yml restart pericopeai-api
  docker compose -p fortress-phronesis -f docker-compose.pericope.yml restart solomonic-clock
  docker compose -p fortress-phronesis -f docker-compose.pericope.yml restart pericopeai-frontend
  ```

## Full Stack Up/Down
- Bring up the whole stack (build if needed):
  ```bash
  docker compose -p fortress-phronesis -f docker-compose.pericope.yml up -d --build
  ```
- Stop and remove containers/volumes:
  ```bash
  docker compose -p fortress-phronesis -f docker-compose.pericope.yml down
  ```

## Status & Logs
- Status: `docker compose -p fortress-phronesis -f docker-compose.pericope.yml ps`
- Logs: 
  ```bash
  docker compose -p fortress-phronesis -f docker-compose.pericope.yml logs -f mysql
  docker compose -p fortress-phronesis -f docker-compose.pericope.yml logs -f augustine-corpus-live
  docker compose -p fortress-phronesis -f docker-compose.pericope.yml logs -f pericopeai-api
  docker compose -p fortress-phronesis -f docker-compose.pericope.yml logs -f solomonic-clock
  docker compose -p fortress-phronesis -f docker-compose.pericope.yml logs -f pericopeai-frontend
  ```

## Local note

If you are on macOS and want the normal local dev stack, do not follow this file.
Use the standalone runbook instead:
- [Local Pericope Stack Runbook](local-pericope-stack-runbook.md)

## Corpus Service (AugustineCorpus)
- Compose in AugustineCorpus repo: `AugustineCorpus/docker-compose.corpus.yml`
- For the normal macOS standalone workflow, use:
  - [Local Pericope Stack Runbook](local-pericope-stack-runbook.md)
- For dev server / prod-like operation, use:
  - `fortress-phronesis/docker-compose.pericope.yml`
  - [dev-server-container-runbook.md](dev-server-container-runbook.md)

## Calculators (askmortgageauthority)
- Repo path assumed: `/root/workspace/calculator.askmortgageauthority.com`.
- From control pane:
  ```bash
  docker compose -f docker-compose.calculators.yml up -d --build
  curl -I http://127.0.0.1:18010
  ```
- Or via script (uses repo compose if present, else build/run):
  ```bash
  bash scripts/deploy-calculators.sh
  curl -I http://127.0.0.1:18010
  ```
- Nginx: proxy `calculators.askmortgageauthority.com` to `http://127.0.0.1:18010`.
- Healthcheck uses curl inside the container; ensure `curl` is in the image.

## WordPress (askmortgageauthority.com) pull helpers
- Set values in `scripts/.env` (defaults in scripts: SSH_HOST=root@vmi2669159, WP_PATH=/var/www/askmortgageauthority, USER=root).
- Pull wp-config:
  ```bash
  bash scripts/pull-wp-config.sh          # saves to ./data/wp-config.php.backup
  ```
- Pull wp-content:
  ```bash
  bash scripts/pull-wp-content.sh         # syncs to ./data/wp-content
  ```
- Dry-run wp-content (optional):
  ```bash
  rsync -avzn --delete "${SSH_HOST}:${WP_PATH}/wp-content/" "./data/wp-content/"
  ```

## Nginx Routing (host)
- `= /api/pericope/guided-prompts` → 127.0.0.1:13080
- `/api` → 127.0.0.1:18000
- `/` → 127.0.0.1:13080
- Config: `/etc/nginx/sites-available/pericopeai.com` (symlinked in sites-enabled)
- Keep the exact-match guided-prompts route above the generic `/api` block.
- Reload after changes: `nginx -t && nginx -s reload`

## Verification
- API: `curl -I http://127.0.0.1:18000/api/docs` and `curl -I https://pericopeai.com/api/docs`
- Clock: `curl -I http://127.0.0.1:8086/api/clock`
- FE: `curl -I http://127.0.0.1:13080` and `curl -I https://pericopeai.com`
- DB: `mysql -h 127.0.0.1 -P 3307 -u${MYSQL_USER:-augustine} -p` (requires local MySQL client)

## Services to Keep
- Host chat API stays on 127.0.0.1:8000 (`chat-api.service`); do not stop it.
- Host nginx and Apache remain for reverse proxy and WordPress (8080).

## Notes
- Compose network `fortress-phronesis-net` is external; leave it in place (Keycloak containers attached).
- If you see the `version` warning in compose, remove the `version:` line to silence it.
- MySQL data persists to `mysql_data`. Defaults come from env vars (`MYSQL_ROOT_PASSWORD`, `MYSQL_DB`, `MYSQL_USER`, `MYSQL_PASS`); override in `.env` before starting.

## WordPress (containerized)
- Compose file: `docker-compose.wordpress.yml` (builds `ama-wordpress:local` from `/root/workspace/askmortgageauthority.com`, runs nginx on host 18020).
- Volumes: `wordpress_data` for core; `/root/workspace/askmortgageauthority.com/data/wp-content` bind-mounted for content.
- DB: no bundled DB; set DB env in `/root/workspace/askmortgageauthority.com/.env` to point to your existing database.
- Start: `docker compose -f docker-compose.wordpress.yml up -d --build wordpress nginx`
- Host nginx: proxy askmortgageauthority.com to `http://127.0.0.1:18020` (keep TLS on host).
