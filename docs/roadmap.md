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
- New Testament persona responses are validated to avoid first-person Jesus identity drift and remain in the selected author voice.

### v1.1.4 — Immediate UI Hardening and Operator Clarity
**Goal:** Ship the next UI updates directly after control simplification, focused on reliability signals, error clarity, and author onboarding readiness.

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

**Implementation Phasing**
- Phase A (service identity + additive data deploy):
  - `service_id/service_version` model, service registry, author-scoped indexing default
- Phase B (API + control plane):
  - service-scoped API endpoints + version pointer promotion/rollback workflow
- Phase C (MDE gate enforcement):
  - required eval schema, baseline diffing, promotion block rules
- Phase D (warehouse + audit hardening):
  - warehouse integration tables, dashboard views, exportable audit trail

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
