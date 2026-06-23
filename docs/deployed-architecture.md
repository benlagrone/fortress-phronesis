# PericopeAI Deployed Architecture

This document is the first operational map for deployed PericopeAI debugging.
Deployment execution remains governed by `docs/pericopeai-deployment.md` and
`docker-compose.pericope.yml`.

## Runtime Topology

- Public domain: `https://pericopeai.com`
- Local app root: `http://pericopeai.local/` when a local hostname router is
  enabled; otherwise `http://localhost:13080/`
- Local performance dashboard: reserve `http://pericopeai.local/performance`
  for local testing. `http://perf.pericopeai.local/` may be added later as an
  alias, but it must point at the dashboard and not replace the app root.
- Host nginx routes:
  - `/api` -> `pericopeai-api` on host port `18000`
  - `/` -> `pericopeai-frontend` on host port `13080`
  - `/api/pericope/guided-prompts` -> frontend/clock proxy path
- Docker compose project: `fortress-phronesis`
- Docker network: `fortress-phronesis-net`

## Services

- `mysql`
  - Container port `3306`; host port `3307`
  - Persists to `mysql_data`
- `augustine-corpus-live`
  - Internal port `8001`
  - Provides corpus retrieval, author catalog, book lookup, and LLM generation
  - Uses per-author index volumes mounted at `/app/indexes/<author_slug>`
- `pericopeai-api`
  - Container port `8080`; host port `18000`
  - Public API surface under `/api`
  - Calls corpus through `CORPUS_API_URL=http://augustine-corpus-live:8001`
- `solomonic-clock`
  - Container port `8080`; host port `8086`
- `pericopeai-assets`
  - Container port `80`; host port `13085`
- `pericopeai-frontend`
  - Container port `80`; host port `13080`

## Chat Request Path

The main browser chat path is:

1. Browser sends `POST /api/v2/chat`.
2. `pericopeai-api` validates API/auth state and session state.
3. API calls corpus `POST /v1/context`.
4. Corpus loads or reuses the selected author vector index and returns retrieved
   context plus metadata.
5. API calls corpus `POST /v1/generate` for the answer.
6. API calls corpus `POST /v1/generate` again for the response summary.
7. API persists chat/session/reference state and returns segmented response data.

VibeVoice/TTS endpoints are separate from this normal chat response path.

## Inference And Retrieval

Production corpus generation uses Fortress LAN Ollama unless explicitly changed:

- `MODEL_PROVIDER=ollama`
- `OLLAMA_BASE_URL=http://192.168.0.126:11434`
- `OLLAMA_MODEL=mistral`
- `OLLAMA_TIMEOUT_SECONDS=120`
- `OLLAMA_CONNECT_TIMEOUT_SECONDS=5`
- Fortress compose explicitly sets `OLLAMA_MODEL=${OLLAMA_MODEL:-mistral}` so
  rebuilds preserve the current live model even if a service env file contains
  an older model value.

Corpus retrieval keeps author indexes in an in-process LRU cache:

- `INDEX_CACHE_SIZE=16` by default in the Fortress compose file.
- `PREWARM_AUTHOR_INDEXES` defaults to:
  `augustine,freud,solomon,plato,paul,marcus_aurelius,john_chrysostom,irenaeus`

## Latency Observability

The API logs sanitized phase timings for:

- `api_corpus_context_complete`
- `api_corpus_generate_complete`
- `api_summary_generate_complete`
- `api_chat_v2_complete`

The corpus logs sanitized phase timings for:

- `corpus_index_loaded`
- `corpus_index_built`
- `corpus_index_cache_evicted`
- `corpus_index_prewarm_complete`
- `corpus_context_complete`
- `corpus_context_endpoint_complete`
- `corpus_generate_endpoint_complete`

These logs report durations and character counts, not prompt bodies.
