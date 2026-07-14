# PericopeAI — Semantic Versioned Feature Roadmap

**Status:** Strawman  
**Purpose:** Planning, alignment, and sequencing  
**Note:** This roadmap is provisional and intended to evolve.
**Linked Backlog:** [Roadmap Recovery Ledger](roadmap-recovery-ledger.md)

---

## Current Roadmap Control State (2026-07-13)

**Status:** sequencing corrected; PericopeAI web product work is not blocked by
the side-repo mobile upstream gap.
**Audit:** [Unpublished Work Audit — 2026-06-22](unpublished-work-audit-2026-06-22.md)

The June control-state section mixed product sequencing with unrelated
publication cleanup and created the wrong next-step signal. The governing
product model is now explicit: PericopeAI's public web stack is organized
around `matter -> counsel -> stack -> synthesis`, and the next public work must
extend that model instead of bypassing it.

### Published / Operationally Closed

- Production Ollama route recovery is operationally closed:
  - Fortress LAN Ollama is the intended production inference provider.
  - Production corpus uses the Fortress UniFi/IPsec private route,
    `MODEL_PROVIDER=ollama`, and `OLLAMA_BASE_URL=http://192.168.0.126:11434`.
  - The production corpus `.env` is the durable runtime source of truth.
  - Fortress deploy preflight accepts the documented Fortress IPsec endpoint
    and rejects local-only Ollama endpoints.
  - Published control-plane commit: `97ff1b3 Guard Pericope Ollama endpoint config`.
- The Ask Proverbs first-pass Pericope implementation has been published:
  - `AugustineCorpus`: `934c05a Route corpus generation through Ollama`
  - `AugustineService`: `e359072 Add Ask Proverbs API contract`
  - `AugustineFE`: `6bae97c Add Ask Proverbs frontend`
- Mobile voice planning has been published in `AugustineFE`:
  - `a818a0b Document mobile voice roadmap scope`
- Solomonic Clock cleanup has been published:
  - `f7e6828 Expose clock guided prompts API`
  - `7773cfa Add clock mobile readiness and launch contracts`
  - `4a5515d Load clock dataset from API with fallback`
  - `fc7dad8 Guard API-first clock dataset loading`
- MDE cleanup has been published:
  - `38c4903 Add candidate grounding promotion workflow`
  - `1957bca Publish refreshed detector reports`
- `pericopeai-mobile-app` is clean and locally committed:
  - `b357260 Add mobile auth voice layout skeleton`
- The divergent Fortress local checkout has been quarantined:
  - old branch preserved as `quarantine/fortress-local-main-20260622`
  - dirty/untracked files preserved as stash `quarantine fortress dirty worktree 2026-06-22`
  - local `main` now tracks clean `origin/main`

### Product Model Lock

- Treat [PericopeAI — Counsel Stacking & Synthesis Implementation Plan](../../docs/pericopeai_implementation_plan.md)
  as governing product intent, not as a side document.
- Public web work should deepen the matter/counsel/synthesis flow already
  implemented in the frontend instead of introducing a competing interaction
  model.
- Pricing and subscription work remains important, but it is a separate
  commercial lane and must not replace the next product-facing commitment.

### Sequenced Product Order

1. The current public surface already establishes the base interaction:
   matter anchor, multi-author counsel stack, and neutral synthesis.
2. The next public commitment is `v1.3.6R` / `v1.3.6`: author-work reader and
   passage-anchored same-author chat.
3. After the reader flow, continue with `v1.2.2` and `v1.2.3` so sessions can
   carry matters, counsels, follow-up questions, and synthesis without prompt
   bloat.
4. After continuity, continue the evidence/review expansion in `v1.3.8A`,
   `v1.3.8B`, `v1.3.9A`, `v1.3.x-OPS`, and `v1.3.x-PROMOTE`.
5. `v1.4.0` and `v1.4.0-ops` stay on the roadmap as a commercial and ops lane,
   but they do not define the next default product build.

### Unfinished Publication / Merge Gate

This remains a real operational follow-up, but it is now scoped correctly as a
side-repo issue rather than the blocker for PericopeAI web-stack sequencing:

- `pericopeai-mobile-app` has no upstream configured, so `b357260` is committed
  locally but not published to a remote.

### Immediate Execution Order

1. Execute `v1.3.6R` / `v1.3.6` as the next public commitment:
   author-work reader, stable range navigation, selected passage anchors, and
   additive `source_context` into same-author chat.
2. After the reader flow, execute `v1.2.2` and `v1.2.3` against the same
   matter/counsel/synthesis model so continuity improves without broad prompt
   replay.
3. Keep `v1.4.0` pricing/subscriptions and `v1.4.0-ops` reliability work as a
   separate commercial and operational lane.
4. Resolve `pericopeai-mobile-app` upstream publication when mobile work
   resumes; do not treat it as the front-of-queue blocker for the web stack.

---

## Semantic Versioning Philosophy

- **MAJOR** — Changes system guarantees, governance, or meaning
- **MINOR** — Adds capability without breaking existing behavior
- **PATCH** — Fixes, performance, or UX refinements only

PericopeAI is treated as a **platform and framework**, not just a website.

---

## Front-of-Queue: Reader-Anchored Counsel Flow

**Status:** next public product commitment.
**Reason:** the counsel stack already exists in the product surface, so the next
clean step is to bind that flow to source reading and passage-anchored
same-author chat rather than jump to a separate commercial surface.

- This front-of-queue slice is defined in detail by `v1.3.6R` in the
  cross-reference release organization and by the `v1.3.6 Reader Follow-On`
  roadmap entry below.
- It should preserve the current matter anchor, Add Counsel flow, and synthesis
  contract while adding direct reading, stable passage selection, and
  same-author contextual asking.
- It should not be expanded into author-acquisition, operator review, pricing,
  or subscription scope.

---

## Separate Commercial Lane: Pricing, Subscriptions, and Invite-Only Access

**Status:** parallel commercial priority; not the default next product-facing
commitment.
**Reason:** PericopeAI still needs a public commercial surface and subscription
wiring, but that work should run as its own lane instead of replacing the
reader-centered product sequence above.

### v1.4.0 — Pricing Page and Stripe Subscription Foundation
**Goal:** Ship a clear PericopeAI pricing page and a Stripe-backed subscription
path while keeping Sacred and Restricted access invite-only.

**Scope**

- Add `/pricing` to `AugustineFE` with Free, Reader, Scholar, Family / Group,
  and Institution tiers.
- Use Stripe Billing with Checkout Sessions for paid public tiers.
- Add backend billing routes for checkout, customer portal, and webhooks.
- Persist subscription state and sync paid roles into the configured
  authorization store.
- Keep Sacred and Restricted access as manually granted entitlements, never
  public self-serve purchases.
- Add regression tests proving a normal paid subscriber cannot access Sacred or
  Restricted content without the matching entitlement.

**Definition of Done**

- Public pricing page exists and explains paid tiers plus invite-only access.
- Stripe test-mode checkout and webhooks work for Reader, Scholar, and
  Family / Group.
- Paid subscriptions assign expected runtime roles.
- Customer Portal sessions can be created for subscribed users.
- Sacred and Restricted access remain invite-only and independent of public
  subscription tier.

### v1.4.0-ops — GitHub-Native Reliability Path
**Goal:** Use GitHub-native tooling to turn Fortress-collected production
failures into actionable bugs while catching code and dependency problems before
deploy.

**Scope**

- Fortress remains the private raw event store.
- GitHub Issues are the sanitized Codex-readable handoff surface.
- Add grouping/fingerprinting for `pericope_error_events`.
- Create or update one GitHub Issue per active failure fingerprint when
  escalation is explicitly enabled.
- Verify Dependabot and CodeQL coverage in the owning application repos.
- Keep raw prompts, request bodies, cookies, auth headers, tokens, and private
  logs out of GitHub issues.

**Definition of Done**

- Fortress can dry-run issue grouping without contacting GitHub.
- With escalation enabled, repeated synthetic failures update one GitHub Issue
  instead of creating duplicates.
- Codex can read the issue and identify the owning repo/service to inspect.
- No secrets or raw user prompts appear in issue bodies.

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

### v1.1.6 — Saved Author Preferences
**Goal:** Let authenticated users keep a durable author preference without letting saved state override stronger route or session context.

- Add authenticated author preference persistence:
  - favorite authors
  - exactly one default author
  - graceful handling when a saved default author is no longer production-visible
- Expose a dedicated authenticated preference surface:
  - `GET /api/v1/user/preferences/authors`
  - `PUT /api/v1/user/preferences/authors`
- Make saved preferences available across the main author-selection surfaces:
  - chat persona panel
  - `/authors` browse page
  - `/authors/:slug` detail page
  - signed-in profile page
- Apply the saved default author only when no stronger context exists:
  - signed-in `/` and `/chat` launch with no explicit author route
  - new chat reset
  - never override `/author/:slug`, session resume, or launch-driven chat state

**Definition of Done**
- Authenticated users can favorite authors and set a default author.
- The default author persists across sessions/devices.
- Signed-in landing and new chat preselect the saved default author when no stronger route/session context exists.
- Invalid or hidden saved defaults degrade safely and are surfaced as warnings instead of silently breaking launch behavior.
- Author preference management is available from chat, browse, detail, and profile surfaces.

**Status (`2026-04-11`)**
- `v1.1.6` is live on the public stack.
- Favorites/default-author persistence is backed by authenticated service endpoints and rendered in chat, browse, detail, and profile surfaces.
- Signed-in landing and new chat now preselect the saved default author without overriding explicit author routes or resumed sessions.

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

### v1.2.3 — Graph Conversation Memory Migration
**Goal:** Move conversation continuity toward a graph-shaped memory layer while keeping prompt context selective, auditable, and reversible.

**Design authority:** [Graph Conversation Memory Migration](graph-conversation-memory-migration.md)

- Treat MySQL as the canonical write store until a later explicit promotion decision.
- Model PericopeAI's core product objects as graph nodes:
  - user
  - session
  - matter
  - message
  - author
  - counsel
  - citation
  - passage
  - topic
  - follow-up question
  - decision
  - synthesis
- Model explicit relationships as graph edges:
  - `OWNS`
  - `HAS_MATTER`
  - `ASKED_AS`
  - `ANSWERED_BY`
  - `USES_LENS`
  - `CITES`
  - `POINTS_TO`
  - `ABOUT`
  - `RAISES`
  - `RESOLVES`
  - `HAS_DECISION`
  - `HAS_SYNTHESIS`
  - `SYNTHESIZES`
  - `AGREES_WITH`
  - `IN_TENSION_WITH`
- Add a relational graph-shaped phase before introducing a new graph DB service:
  - stable IDs for matters, counsel, follow-up questions, decisions, and synthesis
  - edge-like relational tables where needed
  - deterministic bounded context selector
  - reset/inspection controls
- Add a graph DB proof phase:
  - local-only compose profile
  - idempotent backfill from MySQL
  - graph query fixtures for same-matter continuity, same-author follow-up, counsel stacking, synthesis, and relationship memory
  - parity checks against the relational selector
- Add dual-write and read-shadowing only after the proof phase:
  - MySQL-backed graph event/outbox
  - asynchronous graph event replay
  - graph/MySQL divergence metrics
  - graph outage fallback
- Add bounded graph-selected prompt context behind a feature flag:
  - no full transcript dump into prompts
  - deterministic memory ranking
  - explicit selected/excluded memory reasons
  - trace fields for selected graph nodes and edges
- Preserve memory boundaries:
  - no silent promotion of inferred personal facts
  - raw graph topology remains private
  - normal users get memory inspection/reset, not graph internals
  - public endpoints enforce ownership, redaction, and scope limits

**Definition of Done**
- The graph-shaped memory model is documented and mapped to current MySQL state.
- A graph backfill can rebuild the derived graph from canonical MySQL data.
- Chat works with graph memory enabled, disabled, and unavailable.
- Prompt assembly receives a bounded, explainable context bundle rather than full history.
- Same-author follow-up and resumed matters improve without leaking unrelated conversation context.
- Users can inspect and clear durable memory.
- No public endpoint exposes raw graph topology by default.
- Deployment docs and locks are updated if a graph DB service, volume, env var, or port is promoted.

**Constraint**
- The graph DB starts as a derived read model; making it canonical requires an explicit approval, backup/restore proof, deletion proof, rollback proof, and architecture update.

---

## v1.3.x — Cross-Reference Intelligence (Backward Compatible)

**Design authority:** [Citation, Cross-Reference, and Author Discovery Agent Plan](citation-cross-reference-author-discovery-plan.md) and [Reference Intelligence Agents Implementation Plan](reference-intelligence-agents-implementation-plan.md)
**Architecture diagram:** [Reference Intelligence Agents Architecture](reference-intelligence-agents-architecture.mmd)

**Execution plan:** Build this roadmap lane as a structure/capability/agent
sequence:

1. Structure: contracts, fixture passages, review states, target statuses,
   evidence-span validation, and idempotent run records.
2. Capability: deterministic extractor, resolver, edge builder, author-lead
   builder, handoff dry-run, report writer, and validators.
3. Agent orchestration: run scopes, retries, review queues, approval actions,
   acquisition handoff proposals, and reader-reference adapter.

Execution releases:

- R0: planning hygiene and worktree isolation.
- R1: contracts and fixtures.
- R2: dry-run capability CLI.
- R3: citations and resolver capability.
- R4: cross-reference and lead capability.
- R5: local persistence prototype.
- R6: agent orchestration.
- R7: `fortress.local` operator review MVP.
- R8: acquisition handoff dry-run.
- R9: reader reference adapter.
- R10: runtime promotion only if deployment locks, architecture docs, and smoke
  checks are updated in the same change.

This lane may proceed independently while it remains local, fixture-backed,
dry-run, additive, and non-public. It rejoins the locked deployment path when it
adds production DB migrations, public API/UI, scheduled `fortress.lan` runtime,
mutable `fortress.local` operator state, acquisition ledger writes, graph DB,
new service, host port, or environment variable.

### v1.3.x Release Organization (`2026-07-08`)
The newly added `v1.3.x` work is too broad to treat as one release. It now
contains three different delivery classes and they should remain separated:

- public Pericope user features
- local/operator capabilities
- promotion/runtime work that changes production behavior

**Evaluation**

- `v1.3.6 Reader Follow-On` is the cleanest next public user-facing slice:
  bounded UI/API work, direct value, and independent of agent orchestration.
- `v1.3.7` is a separate operator/ops release:
  local-only, MDE-linked, and not coupled to author publication or public UX.
- `v1.3.8` is too large for one release:
  it mixes tracker control, source review, local acquisition, publication
  handoff, and review UI; it must stay split.
- `v1.3.9` depends on disciplined source/review structure:
  it should not jump ahead of acquisition/source-card foundations even though
  its first buildable slice is Augustine-only.
- The reference-intelligence agent lane is foundational:
  its dry-run/local stages should mature before public/runtime promotion is even
  considered.

**Release train**

1. `v1.3.6R — Author Work Reader and Passage-Anchored Chat`
   - features:
     - extend `book_partial` with reader range metadata:
       `entries`, `total_positions`, `previous_position`,
       `next_position`
     - add `/authors/:authorSlug/works/:source` reader route
     - add `Read` actions from author profiles and selected-author chat context
     - add stable deep links for author/work/range state
     - add selected-passage state and a passage-anchored ask composer
     - send additive `source_context` into `/api/v2/chat`
     - prioritize selected passage text as primary evidence while keeping normal
       RAG supplemental
   - excludes:
     - no Add Counsel changes
     - no synthesis changes
     - no acquisition, review-queue, or operator-agent work
   - stop condition: a user can read a work, select a passage, and ask the same
     author about it in one stable public flow
2. `v1.3.7 — local_tools Model Release Watch + MDE Handoff`
   - features:
     - scheduled provider-model polling through MDE-owned catalog snapshots
     - deduped release-event creation keyed by provider/model/first-seen
     - notification delivery for new actionable model events
     - operator actions to inspect release notes and raw diffs
     - benchmark handoff into MDE with run ID and result-link tracking
     - dashboard/event state for `new`, `acknowledged`, `deferred`,
       `resolved`, `ignored`
   - excludes:
     - no Pericope public UI changes
     - no author publication work
     - no acquisition-ledger mutation
   - stop condition: one newly released model creates one actionable event and
     one benchmark handoff path
3. `v1.3.x-RI1 — Reference Intelligence Foundation`
   - features:
     - contracts for references, targets, review states, evidence spans, and
       idempotent runs
     - fixture corpus snippets and validation tests
     - dry-run CLI for extraction and validation
     - deterministic citations/reference extraction capability
     - canonical resolver for author/work/passage/scripture targets
     - cross-reference edge builder
     - author/work discovery lead generation
     - report writer for dry-run evidence packets
   - excludes:
     - no local persistence yet
     - no `fortress.local` review UI
     - no public API/UI or runtime promotion
   - stop condition: dry-run evidence and lead packets exist without
     persistence, review UI, or runtime mutation
4. `v1.3.8A — Author Acquisition Foundation`
   - features:
     - ledger sync validation across both acquisition ledgers
     - status counts, duplicate-name checks, and dry-run diff reporting
     - coverage audit for missed publications in acquired/partial authors
     - `publication_gap_packet` generation
     - candidate author/work proposal packets
     - source-card preparation with provenance, edition, rights, and quality
       notes
     - run artifacts under `tmp/author-acq/`
   - excludes:
     - no full-text download before source approval
     - no indexing, runtime wiring, or production mutation
   - stop condition: bounded acquisition candidates can be reviewed and approved
     before any full-text ingestion
5. `v1.3.8B — Author Acquisition Execution`
   - features:
     - approved local source download and normalization
     - metadata diffs and local file inventory
     - author-scoped index build commands
     - local catalog/profile/portrait/retrieval verification through
       `pericopeai.local`
     - production publication handoff packets and rollback notes
     - public verification evidence requirement before complete status
   - excludes:
     - no autonomous production publish
     - no status promotion when local verification fails
   - stop condition: one approved author/work can move from source approval to
     local verification with governed production handoff prepared but not
     auto-executed
6. `v1.3.9A — Historical Context Pilot`
   - features:
     - capability manifest for
       `author_historical_context_enrichment`
     - source registry with allowed/prohibited use policy
     - evidence-backed claim records for dates, places, timeline, works,
       influences, and reception
     - Augustine-only dry-run claim generation
     - review packet and approved snapshot artifact
     - additive `historical_context` block in local author profile payload
     - safe missing-data rendering path in frontend author profile
   - excludes:
     - no live LCP/MCP dependency in public profile requests
     - no broad multi-author rollout yet
     - no author-acquisition ledger mutation
   - stop condition: one reviewed historical-context snapshot can be exposed in
     profile payloads without request-time external dependencies
7. `v1.3.x-OPS — Operator Review Surface`
   - features:
     - local persistence for runs, packets, approvals, and retries
     - orchestration of bounded jobs and retry behavior
     - `fortress.local` review queues for reference, acquisition, and
       historical-context packets
     - approval/reject/defer/supersede/audit actions
     - acquisition handoff dry-run controls
     - reader-reference adapter for reviewed outputs
   - excludes:
     - no public promotion by default
     - no bypass of review gates through local UI
   - stop condition: operators can review, approve, defer, retry, and audit
     packets from one local surface without bypassing gates
8. `v1.3.x-PROMOTE — Runtime Promotion Gate`
   - features:
     - production DB/API/UI/runtime promotion decision for reviewed
       agent-derived outputs
     - deployment-lock updates
     - architecture-doc updates
     - smoke-check and rollback-path updates
     - explicit approval-path enforcement for promoted data surfaces
   - excludes:
     - no promotion unless the exact runtime contract is documented and tested
   - stop condition: deployment locks, architecture docs, smoke checks, and
     approval paths are updated in the same change as the promotion

**Ordering rule**

- Do not merge `v1.3.6R` with `v1.3.8` or `v1.3.9`; the trust model, rollback
  surface, and validation path are different.
- Do not treat `v1.3.8` as complete until both `v1.3.8A` and `v1.3.8B` are
  closed; `v1.3.8` is not one shippable pass.
- Keep `v1.4.0` pricing/subscriptions as a separate commercial lane; it should
  not absorb the local agent/acquisition work above.

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

**Status Note (`2026-04-06`)**
- Stage 1, Stage 2, and Stage 3 are live in production.
- Normalized passage records and explicit edges persist in the service database, and semantic neighbors now persist in `passage_semantic_similarity` with score/version metadata.
- `/api/v1/services/{service_id}/context`, `/api/v1/chat`, and `/api/v2/chat` now return `semantic_related_passages` beside explicit `derived_references`, and prompt assembly includes compact semantic-neighbor context as a supplemental signal.

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

**Status Note (`2026-04-06`)**
- `SCR-001` is live in production.
- `/api/v1/scripture/verse` now returns structured verse bundles with source witness metadata, canonical translation witnesses, derived notes, and commentary layers, and the References UI can open those bundles directly.

### v1.3.6 Reader Follow-On — Author Work Reader and Passage-Anchored Chat
**Goal:** Let a user open an author's available works from the author page or chat page, read the source text in stable sections, and ask that same author about a selected passage.

**Execution plan:** [Author Work Reader and Passage-Anchored Chat Execution Plan](author-work-reader-passage-chat-execution-plan.md)

**Architecture diagram:** [Author Work Reader and Passage-Anchored Chat Architecture](author-work-reader-passage-chat-architecture.mmd)

- Execution plan:
  - Phase 0: define additive contracts and fixtures for `source_context`, reader
    range payloads, non-Bible author works, scripture-adjacent works, and
    service-side public-author filtering.
  - Phase 1: extend `book_partial` with reader-oriented range metadata
    (`entries`, `total_positions`, `previous_position`, `next_position`) while
    preserving existing `content`, reference, chapter, verse, section, and
    testament fields for legacy reference expansion.
  - Phase 2: add the frontend reader route at
    `/authors/:authorSlug/works/:source`, wire `Read` actions from author
    profiles and selected-author chat context, and render chunked source text
    with stable position anchors and previous/next controls.
  - Phase 3: add selected passage state and a passage-anchored ask composer,
    send additive `source_context` to `/api/v2/chat`, and update prompt
    assembly so selected passage text is primary evidence while normal RAG
    remains supplemental.
  - Phase 4: validate with corpus/service/frontend tests plus local browser
    smoke against `REACT_APP_API_BASE_URL=http://localhost:13080/api`; update
    architecture docs, UI endpoint contracts, and smoke checks if runtime
    behavior is promoted.
- User entry points:
  - author profile works list adds a direct `Read` action for each available work
  - chat author context exposes the selected author's works and can open the same reader
  - reader deep links preserve author slug, source/work identity, and selected position range
- Reader contract:
  - use `book_partial` as the initial source-backed reading surface
  - render text in stable position/range chunks instead of loading full books into the page by default
  - expose previous/next range navigation and selected passage anchors
  - preserve user-facing labels from source metadata (`book`, `work`, `reference`, `chapter`, `section`, `translation`, and source/provenance fields when available)
- Passage-anchored chat contract:
  - add an additive `source_context` / selected-passage payload to `/api/v2/chat`
  - selected passage context includes author slug, book/work, source filename or stable work ID, start/end positions, reference label, and the selected text
  - the selected passage is treated as primary evidence for that turn while normal retrieval may add nearby support
  - same-author follow-up remains visually subordinate and grounded in the selected passage, not converted into an Add Counsel workflow
- Trust and access boundaries:
  - public reader data must pass through the `AugustineService` public-author boundary before it is cached or exposed
  - position values remain retrieval offsets, not canonical verse numbers
  - canonical verse/source-witness behavior stays with the v1.3.6 verse bundle path
  - Source Steward metadata can enrich edition, license, translator, source URL, and rights notes later without changing the reader route shape

**Definition of Done**
- A user can open a work from `/authors/{author_slug}` and read chunked source text.
- A user can open the selected author's works from `/author/{author_slug}` or `/chat` without losing the active chat context.
- Selecting a passage and asking a question sends an anchored `/api/v2/chat` request and receives an answer that cites or names the selected section.
- Reader links are bookmarkable and recover the same author/work/range.
- Existing `/api/v2/chat`, references, verse bundles, and author browse flows remain backward compatible.

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

### v1.3.8 — Author Acquisition Agents
**Goal:** Turn author acquisition from a manually maintained tracker into an operator-assisted workflow that advances authors through source review, local acquisition, indexing, publication handoff, and public verification without bypassing human approval gates.

**Execution plan:** [Author Acquisition Agents Execution Plan](author-acquisition-agents-execution-plan.md)

**Design authority:** [Author Acquisition Agents Execution Plan](author-acquisition-agents-execution-plan.md)

**Architecture diagram:** [Author Acquisition Agents Architecture](author-acquisition-agents-architecture.mmd)

**Status:** Active development. Phase 0 tracker control has started with the
read-only `author-acq` CLI, ledger validation, status reporting, and tracker
audit tests. Remaining roadmap work must stay dry-run-first and approval-gated
until the local acquisition, publication, and public-verification packets exist.

**Roadmap execution sequence**

- R0 — Planning and architecture:
  - keep this roadmap entry linked to the execution plan and `.mmd` diagram
  - preserve the two-plane operating model: `fortress.lan` workers,
    `fortress.local` operator review
  - keep production topology unchanged unless deployment locks, architecture
    docs, and smoke checks are updated in the same change
- R1 — Tracker control:
  - keep both acquisition ledgers synchronized and valid
  - emit `tracker_audit_report`, status counts, duplicate-name checks, unknown
    status warnings, and dry-run ledger diffs
  - add run IDs, JSON artifacts, and daily Markdown reports under
    `tmp/author-acq/`
- R2 — Coverage audit:
  - extract local works from corpus text directories and metadata
  - start with `legacy_runtime_wired` and `texts_present_index_volume_wired`
    cohorts
  - emit `publication_gap_packet` records without source downloads
- R3 — Candidate and source review:
  - turn backlog priorities and reviewed reference-intelligence leads into
    candidate author/work packets
  - prepare `source_card` records with provenance, edition, translator/editor,
    rights status, retrieval date, and source quality notes
  - block full-text ingestion until the source card is approved
- R4 — Local acquisition and indexing:
  - wrap approved corpus download, normalization, metadata, and author-scoped
    index commands
  - emit local file inventory, expected changes, rollback notes, and
    `local_acquisition_run` packets
- R5 — Local runtime verification:
  - verify local catalog, profile, portrait/media metadata, compose wiring, and
    grounded retrieval through `pericopeai.local`
  - keep failed local checks as repair packets, not status promotion
- R6 — Publication handoff and public verification:
  - prepare governed corpus sync/index/restart checklists without executing
    production changes
  - require explicit approval before production mutation
  - require public catalog/profile/media/runtime evidence before complete status
    is allowed
- R7 — Operator review surface:
  - expose run history and review packets through `fortress.local` or a
    compatible JSON export
  - support approve, reject, defer, supersede, retry, and audit-trail actions
  - prevent the UI from bypassing source, local, production, or public gates

- Tracker control:
  - validate both acquisition ledgers before any write path
  - summarize status counts and classify legacy/runtime-wired entries
  - block ledger mutations when semantic or byte-level drift is detected
- Coverage audit:
  - inspect acquired and partially acquired authors for missed publications
  - produce `publication_gap_packet` review records before source lookup or download
  - start with `legacy_runtime_wired` and `texts_present_index_volume_wired` cohorts
- Candidate and source pipeline:
  - propose new author/work candidates with evidence and priority scoring
  - prepare source cards with provenance, edition, and rights/review status
  - keep metadata discovery separate from full-text ingestion
- Local build pipeline:
  - use existing corpus download, normalization, metadata, and index scripts through guarded commands
  - emit local acquisition and runtime verification packets
  - prevent `runtime wired` from being treated as production completion
- Release pipeline:
  - produce publication handoff packets for governed corpus sync/index/restart work
  - require explicit approval for production mutation
  - finalize complete status only after public catalog/profile/media/runtime verification passes
- Monitoring and operator workflow:
  - write local run/review artifacts under `tmp/author-acq/`
  - produce daily review reports until `fortress.local` can render queues
  - later surface review packets in `fortress.local` with approve/reject/defer actions

**Definition of Done**
- `author-acq validate-ledgers`, `status-report`, and `audit-tracker --dry-run` are stable and tested.
- Coverage audit produces reviewable missed-publication packets for at least one acquired or partially acquired author.
- Source cards can be prepared without downloading full text.
- One approved bounded author/work can be acquired locally, indexed, and locally verified.
- Publication handoff can be generated without executing production changes.
- Public verification evidence is required before a complete acquisition status is written.
- `fortress.local` can show review packets or consume a compatible JSON export.

### v1.3.9 — Author Historical Context Capability
**Goal:** Enrich author profiles with reviewed historical context built from
Codex LCP/MCP data sources, Source Steward metadata, local corpus metadata, and
reference-intelligence evidence without making public profile requests depend on
live external sources.

**Execution plan:** [Author Historical Context Capability Execution Plan](author-historical-context-capability-execution-plan.md)

**Architecture diagram:** [Author Historical Context Capability Architecture](author-historical-context-capability-architecture.mmd)

- Capability structure:
  - define `author_historical_context_enrichment` as an agent capability with a
    machine-readable manifest, input/output contracts, source policy, review
    requirement, and no direct publish authority
  - keep this capability reference-intelligence-adjacent, not a public chat
    feature and not an author-acquisition ledger writer
  - represent LCP/MCP providers as enrichment inputs, not runtime dependencies
- Supporting structure:
  - add a source registry that describes allowed source uses, reliability tier,
    rights posture, and prohibited uses such as long-form biography copying
  - create evidence-backed claim records for timeline events, dates, places,
    context, works chronology, influences, contemporaries, and reception
  - preserve confidence, conflict flags, source refs, and review status for
    every candidate public claim
- Operator workflow:
  - run bounded jobs on `fortress.lan` for source planning, source collection,
    identity resolution, claim extraction, conflict detection, draft assembly,
    and validation
  - produce review packets for `fortress.local` with approve/reject/edit/defer,
    merge, needs-source, and rights-concern actions
  - publish only approved local snapshots; do not expose pending/rejected claims
    or operator notes in public payloads
- Profile/API integration:
  - add an additive `historical_context` block to
    `/api/v1/authors/{author_slug}/profile`
  - serve reviewed local snapshots only, with missing-data fallback
  - keep author profile loading and chat functional when historical context is
    absent or unavailable
- First buildable slice:
  - start with Augustine only
  - use local author catalog, biographies, books, portrait metadata, source-card
    fixtures, and optional cached/fixture-backed authority metadata
  - produce period, places, five timeline items, world context, works
    chronology, and influence/reception rows
  - generate a review packet, approve a snapshot, expose it locally, and validate
    profile behavior

**Definition of Done**
- Capability manifest, source registry, snapshot schema, and fixture set exist.
- One Augustine dry-run produces evidence-backed historical claims and a review
  packet without live public runtime dependencies.
- Conflicting or uncertain authorship can be represented without false
  certainty.
- Approved snapshot data appears additively in the local author profile payload.
- Pending, rejected, raw source, credential, and operator-only data remain
  hidden from public profile output.
- Frontend author profile renders historical context with a safe missing-data
  fallback.
- Validation proves no request-time LCP/MCP dependency is introduced.

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
