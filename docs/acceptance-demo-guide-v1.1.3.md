# Acceptance Test + Demo Guide (v1.1.3, Dev)

## Purpose

Run a disciplined dev acceptance pass and a live demo for the v1.1.3 commitment tracks:

1. Pericope Core
2. Solomonic Clock
3. Model Discernment Engine (MDE)
4. Latin RAG Translator

This guide is dev-focused. It does not replace production rollback procedures.

## Scope and Evidence

Store evidence under:

- `fortress-phronesis/tests/author-chat-smoke-visible.jsonl`
- `fortress-phronesis/tests/crossrefs-smoke-visible.json`
- optional screenshots in `fortress-phronesis/tests/acceptance-v1.1.3/`

Recommended setup:

```bash
export FPR_ROOT="/Users/benjaminlagrone/Documents/projects/pericopeai.com/fortress-phronesis"
mkdir -p "$FPR_ROOT/tests/acceptance-v1.1.3"
```

## A) Pericope Core Acceptance + Demo

### A1. Deploy and lock-check (dev)

```bash
cd "$FPR_ROOT"
COMPOSE="docker compose -p fortress-phronesis -f docker-compose.pericope.yml"
FE_COMPOSE="docker compose --env-file ../AugustineFE/.env -p fortress-phronesis -f docker-compose.pericope.yml"

bash scripts/verify-pericope-deploy-lock.sh
docker network create fortress-phronesis-net 2>/dev/null || true

$COMPOSE up -d --build mysql augustine-corpus-live pericopeai-api
$FE_COMPOSE up -d --build pericopeai-frontend
$COMPOSE ps
```

### A1b. Frontend port-binding gate (required)

Verify the frontend service is actually bound to `13080` (not stale `3000`):

```bash
cd "$FPR_ROOT"
docker compose -p fortress-phronesis -f docker-compose.pericope.yml ps pericopeai-frontend
curl -sS -m 10 -i http://localhost:13080 | sed -n '1,5p'
```

If `ps` shows `0.0.0.0:3000->80/tcp` or `curl` to `13080` fails, force recreate frontend:

```bash
cd "$FPR_ROOT"
docker compose --env-file ../AugustineFE/.env -p fortress-phronesis -f docker-compose.pericope.yml \
  up -d --build --force-recreate pericopeai-frontend
docker compose --env-file ../AugustineFE/.env -p fortress-phronesis -f docker-compose.pericope.yml \
  ps pericopeai-frontend
curl -sS -m 10 -i http://localhost:13080 | sed -n '1,5p'
```

### A2. API and chat acceptance tests

```bash
cd "$FPR_ROOT"
curl -fsS http://localhost:18000/api/healthz
curl -fsS http://localhost:18000/api/v1/authors >/dev/null
curl -fsS http://localhost:13080 >/dev/null

python3 scripts/smoke-tests.py \
  --base-url http://localhost:18000 \
  --authors augustine,marcus_aurelius \
  --timeout 60 \
  --max-wait 60 \
  --out tests/author-chat-smoke-visible.jsonl
```

Pass criteria:

1. Lock script returns `Deployment lock check PASSED`.
2. `smoke-tests.py` returns `result: PASS`.

### A3. Crossref acceptance tests

```bash
cd "$FPR_ROOT"
python3 scripts/smoke-crossrefs.py \
  --base-url http://localhost:18000 \
  --author moses \
  --limit 20 \
  --timeout 90 \
  --out tests/crossrefs-smoke-visible.json

curl -sS -i -m 20 'http://localhost:18000/api/v1/crossrefs/books?limit=5'
```

Pass criteria:

1. `smoke-crossrefs.py` returns `Result: PASS (0 failures)`.
2. Route check returns `HTTP/1.1 200 OK`.

### A4. Pericope UI acceptance checklist (manual)

Open `http://localhost:13080` and verify:

1. `Mode` selector is absent.
2. `Test Memory` button is absent.
3. Persona selector is integrated in the author context panel.
4. On desktop (>=1100px), chat is primary and context/references render in right panel.
5. In `Related Authors / Works`, clicking `Open` on a matched work loads a referenced work excerpt (book partial) in-place.
6. `Switch to ...` action is not shown in matched-work detail view.
7. If answer text includes Bible citations (for example `Genesis 2:16-17`), those citations appear in `References` even when not present in retrieval metadata.
8. On mobile viewport, input row remains visible at bottom during chat.

Capture screenshots for desktop and mobile and store in:

- `tests/acceptance-v1.1.3/pericope-desktop.png`
- `tests/acceptance-v1.1.3/pericope-mobile.png`

### A5. Pericope demo script (5 minutes)

1. Show health: `curl -fsS http://localhost:18000/api/healthz`
2. Open UI and select persona.
3. Ask one question and show answer/citations.
4. Open right-side references panel (desktop).
5. Show crossref endpoint response in terminal.

## B) Solomonic Clock Acceptance + Demo

### B1. Data generation and validation

```bash
cd /Users/benjaminlagrone/Documents/projects/pericopeai.com/Solomonic_Seals
python3 src/generate_full_dataset.py
python3 src/validate_json.py
python3 scripts/validate_psalms.py --fail-on-warnings
```

### B2. Runtime smoke

```bash
cd /Users/benjaminlagrone/Documents/projects/pericopeai.com/Solomonic_Seals
PORT=8080 python3 src/webserver.py
```

In another shell:

```bash
curl -fsS http://localhost:8080/api/clock >/tmp/solomonic-clock.json
python3 -c "import json; d=json.load(open('/tmp/solomonic-clock.json')); print(type(d).__name__, len(d) if isinstance(d, list) else len(d.keys()))"
```

Pass criteria:

1. Dataset generation and validators exit `0`.
2. `/api/clock` returns valid JSON.

### B3. Solomonic demo script

1. Open `http://localhost:8080/web/clock_visualizer.html`.
2. Show loaded clock dataset.
3. Show one mapped scripture segment and reference metadata.

## C) Model Discernment Engine Acceptance + Demo

### C1. Baseline validation

```bash
cd /Users/benjaminlagrone/Documents/projects/pericopeai.com/Model_Discernment_Engine
docker compose build
docker compose run --rm mde python3 scripts/list_detectors.py
docker compose run --rm mde python3 scripts/validate_detector_suite.py
python3 scripts/check_pericopeai_contract.py \
  --corpus-base http://localhost:8001 \
  --author paul \
  --question "authority and justice" \
  --top-k 3 \
  --check-book-partial
```

### C2. Live demo run (Ollama-backed)

```bash
cd /Users/benjaminlagrone/Documents/projects/pericopeai.com/Model_Discernment_Engine
docker compose run --rm mde \
  python3 scripts/run_live_ollama_demo.py \
  --profile-id bible_new_testament \
  --models "llama3.2:latest,mistral:latest" \
  --corpus-base http://host.docker.internal:8001 \
  --ollama-base http://host.docker.internal:11434 \
  --store-backend file
```

Pass criteria:

1. Detector and suite validators exit `0`.
2. Contract check exits `0`.
3. Demo run emits a run artifact under `runs/`.

## D) Latin RAG Translator Acceptance + Demo

### D1. Container dev deploy

```bash
cd /Users/benjaminlagrone/Documents/projects/pericopeai.com/latin-rag-translator
docker build -f Dockerfile.api -t latin-rag-translator-api:dev .
docker rm -f latin-rag-api 2>/dev/null || true
docker run -d --name latin-rag-api \
  -p 8010:8010 \
  -e OLLAMA_MODEL=latin-en-trained \
  -e OLLAMA_BASE_URL=http://host.docker.internal:11434 \
  --add-host=host.docker.internal:host-gateway \
  latin-rag-translator-api:dev
```

### D2. API acceptance checks

```bash
curl -fsS http://localhost:8010/health
curl -fsS http://localhost:8010/model-info
curl -fsS http://localhost:8010/translate \
  -H "Content-Type: application/json" \
  -d '{"text":"In principio erat Verbum","direction":"lat-en"}'
curl -fsS http://localhost:8010/translate \
  -H "Content-Type: application/json" \
  -d '{"text":"In the beginning was the Word","direction":"en-lat"}'
```

Pass criteria:

1. `/health` returns `status=ok`.
2. `/model-info` reports expected backend/model.
3. Both translation requests return non-empty `translation`.

### D3. Translator demo script

1. Show `/health` and `/model-info`.
2. Run one `lat-en` and one `en-lat` translation request.
3. Show logs: `docker logs --tail=100 latin-rag-api`.

## Final Sign-Off Checklist (Dev Acceptance)

Mark pass only when all required checks above are green:

- [ ] Pericope lock + smoke + UI checks passed.
- [ ] Solomonic generation + validation + runtime checks passed.
- [ ] MDE detector/suite/contract checks passed.
- [ ] Latin translator health + translation checks passed.
- [ ] Evidence artifacts saved in `tests/`.

## Notes

1. Rollback is a release gate, not part of standard dev acceptance.
2. For release sign-off, pair this guide with:
   - `docs/release-commitment-v1.1.3-all-tracks.md`
   - `docs/release-runbook-prod-v1.1.2.md`
