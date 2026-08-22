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

## Deployment Capability

Production API deploys are owned by Fortress Phronesis. The control-plane helper
is `scripts/deploy-pericopeai-prod.sh`; it verifies the deployment lock, syncs or
validates the sibling `AugustineService` checkout, rebuilds `pericopeai-api`
through `docker compose -p fortress-phronesis -f docker-compose.pericope.yml`,
runs migrations/catalog sync, and smokes the local API plus host TLS vhost.
Pushes that change the mirrored `docs/author_acquisition.json` ledger also invoke
this API deployment runway after the service ledger has been published.
Production frontend deploys are also owned by Fortress Phronesis. Normal
frontend publication starts in `AugustineFE` CI, which build-smokes the pushed
frontend SHA and then sends a `repository_dispatch` event to the Fortress
frontend deploy workflow with the requested `fe_ref` and `fe_sha`. Manual
`workflow_dispatch` in Fortress remains the operator fallback.

Do not use `AugustineService/docker-compose.yml` for production API deploys.

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

## Reader Range Contract

The existing `POST /api/v1/book_partial` route now serves as the reader-range
contract for the author-work reader flow.

- `AugustineCorpus` returns the legacy `content` string plus additive reader
  metadata: `entries`, `total_positions`, `previous_position`, and
  `next_position`.
- `entries` is the selected position window with per-entry `position`,
  `reference`, and `content`; corpus may also include chapter and verse fields
  when that metadata is available.
- `AugustineService` preserves the same additive shape when proxying corpus
  responses and when falling back to service-local text files after upstream
  `404 Book not found`.
- `AugustineFE` now exposes the browser reader route
  `/authors/{author_slug}/works/{source}` and recovers `start` / `end`
  retrieval-position offsets from the URL query string before calling
  `POST /api/v1/book_partial`.
- The reader also allows the user to select one or more passage positions from
  the active range and launch a same-author chat turn from that selection.
  The frontend sends additive `source_context` in `POST /api/v2/chat` with the
  selected `author_slug`, `book`, `source`, `start_position`, `end_position`,
  optional `reference`, and literal selected `content`.
- `pericopeai-api` validates that `source_context.author_slug` matches the
  active persona, then places the selected source text ahead of retrieved
  passages when constructing the chat prompt. Retrieved passages and semantic
  neighbors remain additive supplemental context.
- Response traces prepend a synthetic `selected_source_context` retrieval row
  so audit surfaces can distinguish explicit reader anchors from normal corpus
  retrieval.

This change does not add a new public route, host port, service, or environment
variable. Legacy consumers may continue using `content` only.

## Browser Auth Bootstrap

The public frontend renders immediately as an anonymous guest experience. It
then starts Keycloak silent SSO in the background against
`https://auth.pericopeai.com` using the `pericope` realm and `pericope-web`
client. If the silent SSO iframe or third-party-cookie probe times out, the
browser remains in guest mode and the first render must stay usable. Explicit
Sign In still redirects to Keycloak using Authorization Code + PKCE, and
authenticated API calls attach `Authorization: Bearer ...` after token
exchange/refresh.

The `/history` frontend route is now dual-mode:

- authenticated users load account-backed history from `GET /api/v1/history`
- guests load recent local-only sessions from browser `localStorage`
  (`pericope:lastSessions:v1`)

Guest history is intentionally device-local and additive. It is not synced to
MySQL, does not call the history API, and currently resumes only the locally
stored frontend snapshot for that browser.

## Paid Access Role Boundary

The Keycloak bearer-auth layer now distinguishes plain authenticated users from
paid subscribers.

- `default-roles-pericope` resolves to an authenticated-only runtime role and
  must not be treated as paid access.
- Public paid access must come from an explicit subscription role:
  `reader`, `scholar`, `family_group`, or `institution`.
- Higher paid tiers still satisfy lower reader-class gates; for example,
  `scholar`, `family_group`, and `institution` all satisfy routes that require
  `reader`.
- Invite-only access remains separate from paid access. Sacred / restricted
  authors still require `invited`, `sacred`, `admin`, or `operator` runtime
  roles even when the user already has a paid subscription role.
- `POST /api/v1/user/profile/sync` and the other profile endpoints now return
  the resolved runtime roles plus additive access fields:
  `subscription_tier`, `subscription_tier_label`, `has_paid_access`, and
  `has_invite_only_access`.

## Billing Test Harness

The Pericope API now exposes a deterministic billing test harness for the
commercial lane:

- `GET /api/v1/billing/test/dummy-account` returns the dummy paid-reader account
  contract and the role sets expected after subscription activation.
- `GET /api/v1/billing/status` reports the stored checkout/subscription state
  without mutating the paid-access gate. The current access-state contract is
  `unpaid`, `checkout_pending`, `awaiting_role_sync`, and `paid_active`.
- `GET /api/v1/billing/config/public` exposes a non-secret runtime snapshot of
  the configured billing provider, Stripe mode readiness, publishable/webhook
  wiring state, and the tier lookup keys expected by the public commercial
  lane. This route is intended for public prod verification without requiring a
  Keycloak login.
- `POST /api/v1/billing/checkout/session` creates a subscription-mode checkout
  session through the configured provider. The default local/CI provider is the
  fixture provider, which returns `checkout.stripe.test` URLs and never stores
  Stripe keys in source.
- When `PERICOPE_BILLING_PROVIDER=stripe`, the runtime may operate in Stripe
  test or live mode. `PERICOPE_BILLING_TEST_MODE=true` requires a Stripe test
  key, while `PERICOPE_BILLING_TEST_MODE=false` requires a Stripe live key
  (`sk_live_...` or `rk_live_...`). Mismatched key/mode pairs fail closed at
  runtime instead of silently downgrading to fixture behavior.
- `POST /api/v1/billing/customer-portal/session` creates a customer portal
  session for authenticated accounts.
- `POST /api/v1/billing/test/complete-checkout` completes the fixture checkout
  locally for the authenticated dummy user and records the active subscription
  state without requiring a real Stripe callback.
- `POST /api/v1/billing/webhooks/stripe` processes a Stripe-shaped
  `checkout.session.completed` or `customer.subscription.updated` event and
  returns explicit simulated Keycloak claims / role-sync output. Production
  identity mutation must remain a separate, audited Keycloak operation.

The frontend `/pricing` and `/billing/success` routes consume the billing
endpoints. Billing state persists in MySQL `billing_accounts` independently of
the Keycloak role claims so the commercial state and the runtime access state
can be observed separately. The automated test path covers dummy account ->
checkout -> completion -> role sync simulation -> portal session. Sacred /
Restricted access remains separate from public paid subscription roles.

The separately packaged Expo/React Native client consumes the same billing
status, checkout, and portal endpoints without embedding Stripe or OIDC client
secrets. Guest traffic uses `POST /api/v2/mobile/free/chat` without an API key;
the API bounds that lane to 10 messages per client IP per UTC day and returns
standard rate-limit headers. The initial counter is process-local, which is
appropriate for the current single API process but must move to shared durable
storage before horizontal scaling. Paid traffic uses `POST /api/v2/mobile/chat`,
which requires the Keycloak `reader` role server-side; the existing browser
`POST /api/v2/chat` contract remains unchanged. Native sign-in uses the
`pericopeai://auth` redirect and requires a public PKCE Keycloak client named
`pericope-mobile`. That client and redirect must be verified in the live realm
before paid APK access is considered deployable; free chat does not depend on
Keycloak.

## Chat Request Path

The main browser chat path is:

1. Browser sends `POST /api/v2/chat`.
2. `pericopeai-api` validates API/auth state and session state.
3. API calls corpus `POST /v1/context`.
4. Corpus loads or reuses the selected author vector index and returns retrieved
   context plus metadata.
5. If the request includes reader-selected `source_context`, API injects that
   literal source text as primary evidence for the turn before the retrieved
   context block.
6. API calls corpus `POST /v1/generate` for the answer using the normal
   `CORPUS_GENERATE_MAX_TOKENS` answer budget.
7. API compacts the response summary locally for session state and response
   metadata; summary generation must not issue a second corpus/LLM call.
8. API derives an optional same-author `follow_up_question` segment from the
   answer, explicit session state, and optional compact clock advisory context.
   `clock_followup_weight` may bias the follow-up question angle only; it must
   not change answer grounding or expose raw clock internals.
9. API persists chat/session/reference state and returns segmented response data.
10. `GET /api/v1/history/{session_id}` now restores same-author follow-up
    companions additively through a `message_companions` map keyed by
    `messages[].message_id`. The frontend uses that map to restore follow-up
    prompts on resumed assistant turns without changing the stored message row
    contract.

VibeVoice/TTS endpoints are separate from this normal chat response path.

## Persistence And Memory

MySQL is the current deployed source of truth for PericopeAI application
persistence, including sessions, messages, citations, explicit session state,
relationship memory, response traces, normalized passages, explicit passage
references, semantic passage-neighbor rows, and billing subscription state in
`billing_accounts`.

Unauthenticated browsers may also persist a bounded recent-session cache in
`localStorage` under `pericope:lastSessions:v1` so the guest `/history` route
can resume local sessions without a server round trip. This guest cache is not
canonical persistence, is not shared across devices or browsers, and must not
be treated as proof that a server-backed session exists.

`response_traces` now persist additive `follow_up_question_json` alongside
`assistant_message_id`. That makes the follow-up prompt reproducible for the
history resume path and trace audit surfaces without introducing a second chat
message record or mutating the `messages` table contract.

No graph database is currently deployed in the Fortress-managed PericopeAI stack.
The planned graph conversation memory migration is documented in
`docs/graph-conversation-memory-migration.md`. Until that roadmap item is
implemented and promoted, graph memory is not a runtime dependency and prompt
assembly must continue to work from MySQL-backed session state, recent messages,
relationship memory, corpus retrieval, explicit references, and semantic
neighbors.

## Planned Citation And Reference Agent Layer

The planned citation, cross-reference, and author-discovery workflow is
documented in `docs/citation-cross-reference-author-discovery-plan.md`. The
broader non-Source-Steward reference-agent system that expands that lane is
documented in `docs/reference-intelligence-agents-implementation-plan.md`. It
covers the run orchestrator, citations agent, reference resolver,
cross-reference agent, author discovery agent, acquisition handoff agent,
operator review agent, and reader reference adapter.

The planned split is:

- `fortress.lan` runs bounded citation extraction, resolution, edge-building,
  scoring, and acquisition-lead generation jobs.
- `fortress.local` presents operator review queues for references,
  cross-reference edges, author discovery leads, and acquisition handoff
  proposals.
- `pericopeai.local` and the public PericopeAI app consume only reviewed or
  confidence-gated reference outputs.

The system is evidence-first. Durable references, cross-reference edges,
author-discovery leads, and acquisition handoff proposals must point back to
source evidence, provenance, confidence, and review status. The acquisition
handoff path must not modify author-acquisition ledgers or ingest third-party
text without explicit review and must preserve the gates in
`docs/author-acquisition-process.md`.

This plan does not add a public route, host port, graph database, deployed
service, or environment variable. If any of those are promoted later, update the
workspace deployment lock, this architecture document, and smoke checks in the
same change.

## Planned Author Historical Context Capability

The planned author historical-context capability is documented in
`docs/author-historical-context-capability-execution-plan.md`. It defines the
`author_historical_context_enrichment` agent capability and its supporting
structure for Codex LCP/MCP data-source pulls, source registry policy,
evidence-backed historical claims, operator review packets, and reviewed
author-profile snapshots.

The public PericopeAI profile path must consume only reviewed local snapshots.
It must not call LCP/MCP data sources at request time or expose pending review
claims, raw source responses, connector credentials, or operator-only notes.

The first implementation slice is now defined in code and local fixtures:

- reviewed public snapshots live in
  `AugustineCorpus/metadata/author-historical-context.json`
- `GET /api/v1/authors/{author_slug}/profile` may now return additive
  `historical_context` when a reviewed snapshot exists, or `null` when it does
  not
- the author detail UI renders the reviewed snapshot as dense profile context
  and falls back to biography text when no reviewed snapshot is present
- the Fortress deployment compose file mounts the reviewed snapshot into the API
  container at `/app/metadata/author-historical-context.json`
- the API deploy helper now syncs both `AugustineService` and `AugustineCorpus`
  before rebuild and verifies the Augustine profile historical-context contract
  locally and through the public vhost

This slice still adds no public route, host port, graph database, deployed
service, or environment variable.

## Planned Author Acquisition Agents

The planned author-acquisition operator system is documented in
`docs/author-acquisition-agents-execution-plan.md`. It extends the existing
author-acquisition process with tracker stewardship, publication-gap audits,
candidate scouting, source cards, local acquisition, runtime verification,
publication handoff, public verification, and operator review.
Tracker stewardship is expected to reconcile ledger works inventory against the
mounted AugustineCorpus texts so acquisition status is tied to all acquired
works, not only highlighted titles.

The plan does not add a public route, host port, deployed service, environment
variable, or deployment path by itself. If promoted from plan to runtime, the
workspace deployment lock, this architecture document, and smoke checks must be
updated in the same change.

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
  `augustine,freud,solomon,plato,paul,marcus_aurelius,john_chrysostom,irenaeus,adam_smith,ludwig_von_mises`
- Benjamin Franklin, Thomas Paine, and Thomas Jefferson use direct-uploaded
  `texts/<slug>_texts` directories and dedicated persistent
  `corpus_<slug>_index` volumes in both corpus compose services. Their text
  payloads are intentionally excluded from Git and must be published through
  the corpus upload path before production indexing.

## Latency Observability

The API logs sanitized phase timings for:

- `api_corpus_context_complete`
- `api_corpus_generate_complete`
- `api_summary_generate_complete` with `source=local`
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

## Production Monitoring

Fortress Phronesis owns a scheduled/manual production monitor in
`.github/workflows/monitor-pericope-prod.yml`. It uses the existing deploy SSH
credentials and server checkout path to run `scripts/verify-pericope-prod-smoke.py`
against the public `https://pericopeai.com/api` surface with the server-side API
key from `/root/workspace/AugustineService/.env`.

The monitor verifies:

- `/api/healthz` returns `ok=true` and database health is good.
- `/api/v1/authors` returns the required public author slugs and at least the
  configured minimum visible author count.
- `/api/v2/chat` returns a segmented `status=done` response with non-empty
  answer, citations, summary, books, and metadata.
- `pericopeai-api` logs include `api_summary_generate_complete` with
  `source=local` after the smoke request.
- `pericopeai-api` logs include an `api_chat_v2_complete` marker for the smoke
  session and no chat/corpus/summary failure marker in the smoke window.

The monitor does not rebuild containers, change environment files, or alter
locked compose topology.
