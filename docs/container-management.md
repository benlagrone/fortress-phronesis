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
- Repo path assumed: `/root/workspace/ama-calculators` with `docker-compose.yml` exposing host `18010:8000`.
- Deploy via script:
  ```bash
  bash scripts/deploy-calculators.sh
  curl -I http://127.0.0.1:18010
  ```
- If using compose directly:
  ```bash
  docker compose -f /root/workspace/ama-calculators/docker-compose.yml up -d --build
  ```
- Nginx: proxy `calculators.askmortgageauthority.com` to `http://127.0.0.1:18010`.
- Note: healthcheck in compose uses curl inside the container; ensure `curl` is installed in the image.

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
