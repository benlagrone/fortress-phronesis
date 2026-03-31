# PericopeAI — Semantic Versioned Feature Roadmap

**Status:** Strawman  
**Purpose:** Planning, alignment, and sequencing  
**Note:** This roadmap is provisional and intended to evolve.
**Linked Backlog:** [Roadmap Recovery Ledger](roadmap-recovery-ledger.md)

---

## Semantic Versioning Philosophy

- **MAJOR** — Changes system guarantees, governance, or meaning
- **MINOR** — Adds capability without breaking existing behavior
- **PATCH** — Fixes, performance, or UX refinements only

PericopeAI is treated as a **platform and framework**, not just a website.

---

## v0.x — Pre-Stability (Exploration / Internal Use)

> APIs and behavior are unstable. Breaking changes allowed.

### v0.1.0 — Core Existence
**Goal:** System runs end-to-end.

- FastAPI backend
- Single persona support
- Static corpus ingestion
- Basic RAG pipeline
- Minimal web UI

**Definition of Done**
- User can ask questions and receive grounded responses
- System runs reliably without manual steps

---

### v0.2.0 — Multiple Personas
**Goal:** Persona abstraction exists.

- Persona abstraction layer
- Multiple personas selectable
- Separate corpora per persona
- Persona-specific prompt scaffolding

---

### v0.3.0 — Deterministic Grounding
**Goal:** Reduce ambiguity and prompt leakage.

- Corpus chunking standards
- Retrieval constraints
- Early provenance markers (internal)
- Improved grounding consistency

---

## v1.0.0 — Stable Core

> Safe to build on. Behavior is predictable.

### v1.0.0 — Persona Stability
**Goal:** Personas are repeatable and defensible.

- Formal persona specification template
- Corpus eligibility rubric
- Clear separation of:
  - persona rules
  - grounding corpus
  - reference material
- Repeatable persona creation workflow

**Guarantees**
- Personas behave consistently
- Adding a persona does not alter existing personas

---

## v1.1.x — Transparency & Control (Backward Compatible)

### v1.1.0
**Goal:** User understands how answers are produced.

- Persona modes (e.g. interpretive, analytical)
- Epistemic labeling:
  - textual
  - interpretive
  - speculative
- Optional citations

### v1.1.1 – v1.1.x
- UX refinements
- Performance improvements
- Bug fixes only

### v1.1.2 — Author Context Header (DB-Backed)
**Goal:** Show grounded author context immediately when a persona is selected.

- Add a top-of-chat UI element that updates on persona selection
- Display:
  - selected author name
  - author summary/description
  - authoritative books/works list
- Data source requirements:
  - author identity and summary from author info in DB
  - books/works list from book metadata in DB
  - no hardcoded FE author/book lists
- API support:
  - endpoint (or extension) that returns author profile + books metadata in one payload
  - stable ordering for books list
  - caching headers for read performance
- Technical requirements:
  - add relational catalog tables for authors and author_books (or equivalent normalized model)
  - add migration/seed job to populate catalog tables from canonical corpus sources
  - runtime reads for this header must come from DB-backed catalog queries
  - file-only runtime sources (`author_index.json`, `book_metadata.json`) are not compliant for this feature
  - add contract tests that fail if API returns empty books for a valid production-visible author
- UX behavior:
  - updates instantly when dropdown selection changes
  - loading and empty-state handling
  - hidden for invalid/unknown author selections

**Definition of Done**
- Selecting an author updates the header with DB-backed author + books data.
- Header data matches backend metadata for the selected author.
- Works for all production-visible authors (including newly added authors) without FE code changes.

### v1.1.3 — Augustine Frontend Control Simplification
**Goal:** Reduce top-of-chat UI complexity while preserving author grounding visibility.

- Remove the `Mode` selector from the chat controls
- Remove the `Test Memory` control from the chat controls
- Combine the remaining top control element (persona selector) directly into the author context element as one unified panel
- Keep author profile visibility in the merged panel (name, summary, key works)
- Preserve current persona-selection behavior while simplifying layout
- Improve mobile viewport behavior so chat message area fills remaining screen height and keeps the input/send row visible without page over-scroll
- Add a conversation tuning guardrail for New Testament personas: the assistant must never adopt Jesus' first-person persona; it must respond as the selected author (e.g., Luke, John, Paul) and refer to Jesus in third person

**Definition of Done**
- The top chat area no longer shows `Mode` or `Test Memory`.
- Users can select persona from within the author context element (single combined panel).
- Existing author-context data flow remains DB-backed and functional.
- On mobile, the chat window fits within viewport height minus controls, with message list scrolling independently while input/send remains visible at the bottom.
- Bible-author persona responses are validated to avoid first-person divine-speaker identity drift and remain in the selected author voice.

**Status (`2026-03-30`)**
- `v1.1.3` UI carry-over is closed, including live `UI-005` verification for Bible-author personas on the public stack.

### v1.1.4 — Immediate UI Hardening and Operator Clarity
**Goal:** Ship the next UI updates directly after control simplification, focused on reliability signals, error clarity, and author onboarding readiness.

**Carry-Over Rule (`2026-03-28`)**
- `v1.1.4` is carry-over UI work that was left open while later platform work advanced.
- No work may advance to newer roadmap scope until all unfinished `v1.1.x` UI carry-over items are closed.
- Execution order is:
  - finish `v1.1.4` UI carry-over (`UI-006`, `UI-007`)
  - only then resume forward roadmap work

- Responsive layout behavior by viewport:
  - mobile keeps the current single-column format (chat-first)
  - large desktop moves author context and references/citations into a right-side panel while chat remains primary
- Add explicit request-state UI for chat:
  - sending
  - retryable error
  - timeout state
  - recovered/success state
- Standardize API/auth error banners with actionable copy:
  - `401` (invalid/missing key or token)
  - `403` (insufficient access profile)
  - `504` (upstream timeout / retry guidance)
- Add a lightweight environment/build badge in UI footer/header:
  - environment (`prd`/`qa`/`dev`)
  - app build version
  - generated-at timestamp (if available)
- Improve session usability in chat history:
  - clearer persona label in each session row
  - last-updated timestamp formatting consistency
  - explicit "resume session" affordance
- Add "new author readiness" UI guardrails:
  - empty author profile handling with non-breaking fallback state
  - books/works panel handles zero-book metadata without layout shift
  - unknown author slug routing returns controlled UI state (not blank screen)
- Add immediate reference-completeness guardrail (small fix):
  - infer Bible-style citations from answer text and render them in References when retrieval metadata is incomplete
  - example target: Augustine answer mentions `Genesis 2:16-17` -> References includes `Genesis 2:16-17`
  - inferred rows are non-destructive additions and do not replace corpus-native references

**Definition of Done**
- On large desktop, author context and references are rendered in a persistent right panel; chat remains the main reading/writing column.
- On mobile, chat uses viewport-aware height so message area is focused and the input + send controls remain visible at the bottom.
- On mobile, users can still scroll the page to review additional citations/references without losing access to message entry controls.
- Users can distinguish auth failure vs timeout vs generic failure from UI alone.
- Chat request lifecycle is visible and recoverable without page refresh.
- Build/environment indicators are visible for support and incident triage.
- History/session UI allows predictable resume behavior across personas.
- Newly promoted authors render safely even when metadata is partial.
- Bible citations present in answer text are surfaced in References even when not returned in metadata.

**Status (`2026-03-31`)**
- `v1.1.4` carry-over UI hardening is closed on the public stack.
- `UI-006` request-state and explicit `401` / `403` / `504` handling is live and verified.
- `UI-007` desktop right-side context/references layout with mobile single-column behavior is live and verified.
- Verification artifact: [ui-006-ui-007-public-verification-20260331.md](../tests/ui-006-ui-007-public-verification-20260331.md)

---

## v1.2.x — Memory (Scoped and Explicit)

### v1.2.0
**Goal:** Continuity without drift.

- Session-scoped memory
- Persona-isolated memory
- Explicit memory boundaries

### v1.2.1+
- Memory inspection
- Reset / disable controls

### v1.2.2 — Purposeful Conversation State & Relationship Memory
**Goal:** Make chats feel conversational, goal-directed, and resumable across time without introducing silent drift.

- Add explicit conversation state persisted beside raw messages:
  - `current_goal`
  - `stage`
  - `open_questions`
  - `next_best_action`
  - `promises_made`
  - rolling session summary
- Change prompt assembly order so responses are built from:
  - active conversation state
  - rolling session summary
  - recent turns
  - retrieved corpus context
- Add response-policy guardrails so each answer must:
  - acknowledge what changed
  - orient around the current objective
  - advance the conversation by one purposeful step
  - preserve durable facts that were explicitly provided or confirmed
- Add durable user/relationship memory keyed by authenticated identity or verified lead identity:
  - organization
  - project type
  - timeline
  - constraints
  - prior decisions
  - follow-up commitments
- Treat browser intake as conversation seed data instead of one-shot capture:
  - lead intake initializes memory/session state
  - later sessions can resume from the same relationship context
- Keep memory boundaries inspectable and reversible:
  - no silent promotion of inferred personal facts into long-term memory
  - reset/disable controls remain explicit

**Definition of Done**
- Chats no longer depend only on the last few turns for continuity.
- A resumed session can recover the active goal, current stage, and next best step.
- Lead/intake-originated conversations can continue as long-term threads.
- Durable memory remains explicit, inspectable, and resettable.

**Constraint**
- No silent or implicit long-term memory

---

## v1.3.x — Cross-Reference Intelligence (Backward Compatible)

### v1.3.0
**Goal:** Cross-reference scripture, Church Fathers, and works as first-class data.

- Kickoff milestone (bootstrap): ship deterministic cross-reference API surfaces backed by canonical metadata map:
  - `GET /api/v1/crossrefs/books`
  - `GET /api/v1/crossrefs/books/{book_id}`
  - `GET /api/v1/crossrefs/authors/{author_slug}`
- Canonical reference normalization:
  - Bible refs (book/chapter/verse)
  - Author/work IDs
  - Segment IDs (`author/source/chapter/position`)
- Cross-reference index/graph:
  - author -> Bible passage
  - author -> author
  - author -> work
  - Bible passage -> Bible passage
- Reference types:
  - explicit citation
  - quoted text
  - mention
  - allusion (confidence-scored)
- Query surfaces:
  - API endpoints for forward and reverse lookup
  - UI panel for "Referenced Scripture" and "Related Authors/Works"
- Governance:
  - evidence snippet and confidence on every derived reference
  - versioned extraction runs for reproducibility

**Definition of Done**
- A user can open a response and see indexed cross-references.
- A user can query reverse links (for example: who references Genesis).
- References are exportable and traceable to source segments.

### v1.3.1 — Serviceized Persona Deployment ("X as a Service")
**Goal:** Treat each author/work corpus as a first-class service with independent versioning, deploys, and rollback; use MDE as promotion gate.

- Introduce canonical service identity (not tied to UI labels):
  - `service_id` examples:
    - `augustine.en`
    - `solomon.expanded.en`
    - `psalms.masoretic.en`
    - `psalms.vulgate.la`
    - `grimoire.<tradition>.<lang>`
  - `service_version` for active package pointer
- Define service package ("model pack") contract:
  - retrieval index artifact(s)
  - corpus metadata (books/works/provenance/visibility)
  - persona prompt/policy config
  - compatibility metadata (`schema_version`, `built_at`, `checksum`)
- Separate release types:
  - **code release** (API/FE/runtime)
  - **data/service release** (new author/work, index refresh, pack promotion)
- Deployment strategy for frequent author additions:
  - author/service-scoped indexing by default (no implicit full reindex)
  - additive pack publishing and activation via version pointer switch
  - deterministic rollback to prior service pointer
- API evolution (backward compatible):
  - preserve existing `/api/v2/chat`
  - add service-scoped surfaces:
    - `POST /api/v1/services/{service_id}/chat`
    - `POST /api/v1/services/{service_id}/context`
    - `GET /api/v1/services/{service_id}/metadata`
    - `GET /api/v1/services/{service_id}/version`
    - `GET /api/v1/services`
- Warehouse integration (hybrid model):
  - keep APIs for online serving/auth/rate limiting
  - add warehouse-friendly tables for batch/eval workflows:
    - `service_catalog`
    - `service_versions`
    - `eval_runs`
    - `eval_results`
    - `promotion_decisions`
- MDE promotion gate requirements (mandatory for production promotions):
  - required run tags:
    - `run_id`, `service_id`, `service_version`
    - `llm_provider`, `llm_model`
    - `prompt_version`, `dataset_version`, `timestamp`
  - thresholded metrics:
    - grounding/citation accuracy
    - persona fidelity
    - theological consistency
    - safety/policy compliance
    - latency/cost ceilings
  - promotion blocked on hard-threshold failure or critical non-regression failure
- Operational controls:
  - signed evaluation artifact required for promotion
  - post-deploy smoke + MDE canary check before final promotion
  - automatic rollback trigger on critical regression

**Definition of Done**
- New author/service can be deployed without full-system reindex.
- Each `service_id` has independent `service_version` promotion and rollback.
- MDE gate runs are attached to every production promotion decision.
- Operators can query active version, baseline, and promotion history per service.
- Existing clients using `/api/v2/chat` continue to work unchanged.

**Release Boundary (`2026-03-26`)**
- Treat `v1.3.1` as feature-complete once one canonical service proves the full local operator loop:
  - author-scoped deploy without full-system reindex
  - service version promote
  - service version rollback
  - mandatory promotion gate on promote
  - auditable promotion history
- After that boundary is met, do not add more `v1.3.1` feature scope.
- Remaining work may only be:
  - public/prod deployment alignment
  - access/env issues needed to publish the already-finished feature set
- Public/prod deployment alignment was completed on `2026-03-27` via control-plane GitHub Actions deploy proof; `v1.3.1` is closed.
- Do not hold `v1.3.1` open for broader warehouse/dashboard ambitions once the audit tables and promotion history contract exist locally.

**Implementation Phasing**
- Phase A (service identity + additive data deploy):
  - `service_id/service_version` model, service registry, author-scoped indexing default
  - Commenced 2026-03-16 with registry-backed `service_catalog/service_versions` plus additive `/api/v1/services` read surfaces
- Phase B (API + control plane):
  - service-scoped API endpoints + version pointer promotion/rollback workflow
- Phase C (MDE gate enforcement):
  - required eval schema, baseline diffing, promotion block rules
- Phase D (warehouse + audit hardening):
  - warehouse integration tables, dashboard views, exportable audit trail
  - deferred beyond `v1.3.1` release closure once the `2026-03-26` boundary above is satisfied

### v1.3.2 — Reference Inference Engine (Cross-Author / Cross-Work)
**Goal:** Make inferred references first-class and traceable across Bible and non-Bible corpora.

- Build a deterministic inference pipeline for references across:
  - scripture citations
  - author -> author mentions
  - author -> work mentions (for example: Socrates -> Plato -> Republic)
- Source inputs for inference:
  - answer text
  - retrieved excerpt text (`metadata.excerpt`)
  - canonical author/work catalogs
- Reference provenance model in API/UI:
  - `retrieved`
  - `inferred_from_answer`
  - `inferred_from_excerpt`
- Open behavior:
  - inferred references resolve through canonical author/work mapping and open via `book`/`book_partial` where available
- Evaluation and quality gates:
  - precision/recall samples for inferred references
  - false-positive controls (name collisions, ambiguous work titles)
  - reproducible extraction test fixtures

**Definition of Done**
- Non-Bible personas can surface Bible references and cross-author/work references in References.
- Users can open inferred references to concrete source content when mappings exist.
- Every inferred reference row includes provenance and is auditable.

### v1.3.3 — Graph Exposure Boundary (Infrastructure Private, Insights Public)
**Goal:** Keep the cross-reference graph as internal infrastructure while exposing user-facing evidence and relationships.

- Treat the graph as internal system infrastructure, not a default product surface.
- Keep private:
  - ontology definitions
  - full graph model/adjacency structure
  - internal corpus linkage strategy
- Expose to users:
  - grounded insights
  - citations
  - related author/work/scripture references
- UI contract:
  - default UX shows "Related Passages/Authors/Works" and evidence snippets, not node-network diagrams
  - references remain traceable to source passages
- Optional graph-view support is role-gated (research/admin only) and returns constrained/derived views, not raw internal topology.
- Any public/marketing graph visual must be illustrative only and decoupled from production graph internals.

**Definition of Done**
- Standard user flows return references and relationship summaries without exposing raw graph internals.
- No production public endpoint exposes ontology internals or full graph export by default.
- Role-gated research views are audited and enforce scope, rate, and access controls.

### v1.3.4 — Text-First Graph Construction Pipeline
**Goal:** Build the cross-reference graph from structured passages and automated extraction instead of manual link authoring.

- Stage 1: structured passage foundation (passage is primary key):
  - required normalized fields: `passage_id`, `author`, `work`, `location`, `text`
  - optional enrichment fields: `biblical_refs`, `topics`, `source_edition`, `language`
- Stage 2: automated reference extraction into explicit edges:
  - Bible reference detection (regex + canonical book/verse normalization)
  - author mention detection (canonical author catalog)
  - work-title detection (canonical work catalog)
  - optional LLM-assisted extraction with confidence scoring
- Persist extracted links in a relational reference table (graph-ready, no graph DB requirement):
  - `source_passage_id`
  - `target_type` (`bible`, `author`, `work`)
  - `target_value`
  - `confidence`
  - `provenance` (`regex`, `catalog_match`, `llm`)
- Stage 3: semantic expansion:
  - embeddings over passages
  - similarity edges persisted as `semantic_similarity` with score/version metadata
- Retrieval behavior:
  - query returns primary passages + explicit references + semantic neighbors
  - prompt assembly surfaces related passages as citations/references, not opaque latent links

**Definition of Done**
- Ingested corpora produce normalized passage records across authors/works.
- Extraction jobs generate auditable explicit-reference edges with measurable quality gates.
- Similarity edges are versioned and queryable without blocking core explicit-reference flows.
- Runtime retrieval can return: primary passage, explicit related references, and semantic related passages in one response contract.

### v1.3.5 — Committed Expansion Scope (Snapshot: 2026-03-09)
**Goal:** Convert v1.3 roadmap intent into explicit committed deliverables for features and author rollout.

- Feature commitments (backward compatible):
  - enforce v1.3.3 graph boundary in public UX/API (insights/citations exposed; raw internal topology not exposed by default)
  - deliver v1.3.4 Stage 1 and Stage 2 in production (normalized passage records + explicit reference extraction tables)
  - complete v1.3.2 provenance surfacing end-to-end in API/UI (`retrieved`, `inferred_from_answer`, `inferred_from_excerpt`)
  - ship v1.3.4 Stage 3 semantic-similarity references as supplemental signals (non-destructive to explicit grounding)
  - complete v1.3.1 Phase A for author/service-scoped additive deploys (no implicit full-system reindex per author addition)
- Author commitments:
  - maintain support for the current production-visible author set (52 authors at snapshot time)
  - promote near-ready authors:
    - Eusebius Pamphilus
    - John Chrysostom
  - promote downloaded-but-not-indexed authors:
    - Niccolò Machiavelli
    - Epictetus
    - Seneca
    - Musonius Rufus
  - keep Aristotle as next acquisition target after the committed promotions above
  - treat Solomon coverage as satisfied by existing `solomon` and `solomon_expanded` personas
- Deferred (not committed in this release train):
  - bulk promotion of the remaining pending acquisition backlog until extraction quality gates and serviceized deploy gates are stable

**Definition of Done**
- v1.3.2/v1.3.3/v1.3.4 feature commitments above are implemented and validated in smoke + contract checks.
- Author onboarding flow can add committed authors without full-system reindex.
- The six committed non-live authors above are production-visible with profile metadata and passing author/profile and chat smokes.

### v1.3.6 — Verse Bundle and Original-Language Insight
**Goal:** Let a user open cited scripture at the verse level and inspect the original-language witness, real translation witnesses, lexical meaning, and explicit commentary layers without collapsing them into one opaque AI answer.

- Canonical verse bundle keyed by normalized scripture reference (`book_id/chapter/verse`):
  - source witness metadata (`masoretic`, `critical_greek`, `vulgate`, or other supported witness IDs)
  - original-language verse text
  - transliteration when available
  - one or more canonical English translation witnesses (`kjv`, `drc`, and other licensed/available translations)
  - derived artifacts stored separately from canonical text:
    - `literal_gloss`
    - `expanded_translation`
    - `key_term_notes`
- User interaction contract:
  - References panel adds `See original language` for Bible citations with normalized verse metadata
  - default open behavior is one verse
  - optional contiguous expansion is capped at three verses
  - `book_partial` remains the reading-context surface; it is not the default translation unit for original-language rendering
  - panel keeps `Open chapter` / `Open book` as a separate reading action
- Service/API contract:
  - add verse-focused scripture endpoint (for example `GET/POST /api/v1/scripture/verse`)
  - request resolves by canonical reference, not paragraph position
  - response returns a structured verse bundle that can be rendered directly in UI and optionally injected into chat context
- Data and trust model:
  - persist authoritative source verses and real translation witnesses as source-of-truth data
  - do not present model output as canonical translation
  - cache/persist generated glosses and expanded renderings only as derived artifacts with `model_version` and `prompt_version`
- Lexical and commentary layering:
  - keep lexical facts separate from interpretive commentary
  - expose key-word insight at the word/lemma level, not only at paragraph level
  - allow patristic or tradition-specific commentary (for example Augustine) as an explicit, labeled layer beside the lexical/source layer
- Conversational enrichment:
  - when a user asks about a cited verse or a specific Hebrew/Greek word, chat may prepend a compact verse bundle to prompt context
  - chat responses should distinguish:
    - what the source text says
    - what a key term can mean
    - what a commentary tradition infers from it

**Definition of Done**
- A user can click a cited Bible verse and see original-language text plus at least one real English translation witness in the same panel.
- The UI labels source text, canonical translation, and derived explanation as separate layers.
- Verse-level lookup is grounded by canonical reference and does not depend on paragraph-only RAG resolution.
- Conversational answers about a verse can be grounded in the verse bundle instead of relying only on English excerpt retrieval and persona prompting.


### v1.3.7 — `local_tools` Model Release Watch + MDE Test Handoff
**Goal:** Make the local control plane detect newly released provider models, notify the operator once, and hand off directly into MDE benchmarking.

- Ownership boundary:
  - MDE owns provider catalog polling, snapshot diffing, and release metadata normalization.
  - `local_tools` owns scheduling, alert lifecycle, dedupe, notification routing, and operator actions.
- Polling contract:
  - scheduled job runs the MDE model poller (default cadence: daily)
  - consumes `output/model_catalog_watch/latest.json`
  - evaluates `changed`, per-provider diffs, model IDs, and release-notes URLs
- Alert model:
  - create one actionable control-plane event per stable change key: `provider:model_id:first_seen`
  - event states: `new`, `acknowledged`, `deferred`, `resolved`, `ignored`
  - do not recreate the same event every day unless the underlying model diff changes materially
- Notification policy:
  - immediate alert for newly seen model IDs
  - one-time alert for removed models or meaningful metadata changes
  - provider polling failure escalates only after N consecutive failures
  - initial notification channel is email; webhook/Slack/SMS can follow later
- Operator actions:
  - open provider release notes
  - inspect the raw model diff payload
  - trigger an MDE benchmark run with the new model prefilled
  - mark ignore/defer with an explicit reason
- Required `local_tools` data surfaces:
  - `model_release_watch_runs`
  - `model_release_events`
  - `notification_events`
  - `benchmark_requests`
- Benchmark handoff contract:
  - `local_tools` submits provider/model identity into the MDE run workflow
  - MDE returns run ID, status, and report links
  - the control plane stores benchmark status against the originating release event
- UI contract:
  - dashboard card for new models awaiting benchmark
  - event detail shows provider, model ID, first-seen timestamp, release-notes URL, and benchmark status
  - filters include `unseen`, `awaiting benchmark`, `benchmarked`, and `dismissed`
- Auditing:
  - retain alert history, notification attempts, and benchmark launch/result linkage
  - keep dedupe keys and first-seen timestamps stable across restarts

**Definition of Done**
- `local_tools` runs scheduled model-release polling through MDE.
- A newly seen provider model creates exactly one actionable event.
- Email notification is sent once per new actionable event.
- An operator can trigger an MDE benchmark from the control plane without manual CLI assembly.
- The control plane records benchmark status and report link back onto the originating event.

---

## v2.0.0 — Governance & Auditability (Breaking)

> Institution-ready. Auditable and explainable.

### v2.0.0
- Corpus versioning
- Prompt and configuration diffing
- Response traceability
- Admin audit surfaces
- Best-effort reproducibility

**Breaking Rationale**
- Governance changes system guarantees

---

## v2.1.x — Platform Hardening

- Role-based admin access
- Read-only observability
- Exportable logs and configs
- Deployment profiles (local, VPS, institutional)

---

## v3.0.0 — Platformization (Optional Future)

> PericopeAI as a framework.

- Persona registry / marketplace
- Public API contracts
- Plugin architecture
- Multi-tenant support

**Breaking by design**

---

## Explicit Non-Goals

- Growth hacking
- Social features
- Mass consumer optimization
- Opaque or persuasive AI behavior

PericopeAI prioritizes **intellectual integrity, transparency, and control**.

---

## Execution Pattern (Codex-First Delivery)

- Define architecture and behavior first; implement through concrete backlog tasks.
- Prefer task specs with explicit inputs/outputs, schema, and acceptance criteria over ad hoc snippet requests.
- Use Codex to implement across files, run validations, and produce integrated repo changes.
- Keep architecture/design discussion in planning docs; keep code generation and refactors in Codex execution loops.
