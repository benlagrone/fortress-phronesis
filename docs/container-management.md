# Container Management (PericopeAI)

Repo root: `/root/workspace/fortress-phronesis`
Compose file: `docker-compose.pericope.yml`
Services: `pericopeai-api` (host port 18000 → container 8080), `pericopeai-frontend` (host port 13080 → container 80)
Network: external `pericope_net`

## Update & Rebuild
- Backend only (after pulling AugustineService code):
  ```bash
  docker compose -f docker-compose.pericope.yml up -d --build pericopeai-api
  ```
- Frontend only (after pulling AugustineFE code):
  ```bash
  docker compose -f docker-compose.pericope.yml up -d --build pericopeai-frontend
  ```
- Restart without rebuild (config-only):
  ```bash
  docker compose -f docker-compose.pericope.yml restart pericopeai-api
  docker compose -f docker-compose.pericope.yml restart pericopeai-frontend
  ```

## Status & Logs
- Status: `docker compose -f docker-compose.pericope.yml ps`
- Logs: 
  ```bash
  docker compose -f docker-compose.pericope.yml logs -f pericopeai-api
  docker compose -f docker-compose.pericope.yml logs -f pericopeai-frontend
  ```

## Run Locally for Testing (optional)
- Build and start both services locally (adjust paths/ports as needed):
  ```bash
  docker compose -f docker-compose.pericope.yml up -d --build
  ```
- Hit locally:
  ```bash
  curl -I http://127.0.0.1:18000/api/docs   # API
  curl -I http://127.0.0.1:13080            # Frontend
  ```
- Stop:
  ```bash
  docker compose -f docker-compose.pericope.yml down
  ```

## Corpus Service (AugustineCorpus)
- Compose in AugustineCorpus repo: `AugustineCorpus/docker-compose.corpus.yml`
- Run corpus only:
  ```bash
  docker network create pericope_net || true
  docker compose -f AugustineCorpus/docker-compose.corpus.yml up -d AugustineCorpus-1.0.0
  ```
- Optional indexer (on-demand):
  ```bash
  docker compose -f AugustineCorpus/docker-compose.corpus.yml --profile index run --rm pericopeai-indexer
  ```
- API wiring: set `CORPUS_API_URL` to `http://augustine-corpus-live:8001` (default in compose) so API talks to corpus over `pericope_net`.
- Main compose (`docker-compose.pericope.yml`) includes a placeholder `augustine-corpus-live` service; set `CORPUS_IMAGE` to your built image tag or deploy corpus via its own compose above.

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
- `/api` → 127.0.0.1:18000
- `/` → 127.0.0.1:13080
- Config: `/etc/nginx/sites-available/pericopeai.com` (symlinked in sites-enabled)
- Reload after changes: `nginx -t && nginx -s reload`

## Verification
- API: `curl -I http://127.0.0.1:18000/api/docs` and `curl -I https://pericopeai.com/api/docs`
- FE: `curl -I http://127.0.0.1:13080` and `curl -I https://pericopeai.com`

## Services to Keep
- Host chat API stays on 127.0.0.1:8000 (`chat-api.service`); do not stop it.
- Host nginx and Apache remain for reverse proxy and WordPress (8080).

## Notes
- Compose network `pericope_net` is external; leave it in place (Keycloak containers attached).
- If you see the `version` warning in compose, remove the `version:` line to silence it.

## WordPress (containerized)
- Compose file: `docker-compose.wordpress.yml` (builds `ama-wordpress:local`, runs nginx on host 8081).
- Volumes: `wordpress_data` for core; `./data/wp-content` bind-mounted for content.
- DB: optional `db` service under profile `with-db`; otherwise set DB env in `.env` to point to existing DB.
- Start (without bundled DB): `docker compose -f docker-compose.wordpress.yml up -d --build wordpress nginx`
- Start with bundled DB: `docker compose --profile with-db -f docker-compose.wordpress.yml up -d --build`
- Host nginx: proxy askmortgageauthority.com to `http://127.0.0.1:8081` (keep TLS on host).
