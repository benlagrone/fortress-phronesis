# Author Historical Context Capability Execution Plan

**Status:** planned

**Owner surface:** Fortress Phronesis docs, PericopeAI corpus metadata, and reference-intelligence operator workflows

**Runtime target:** Fortress LAN background jobs with local operator review

**Current deployed source of truth:** existing author profile payloads, author catalog metadata, corpus metadata files, MySQL, and reviewed local artifacts

**Deployment note:** This plan does not add a deployed service, public route, host port, environment variable, or live public dependency by itself.

## Purpose

PericopeAI author profiles need historical context that explains the world each
author speaks from: period, places, intellectual setting, religious and political
environment, works in sequence, influences received, contemporaries, and later
reception.

This plan turns that need into an agent capability:

`author_historical_context_enrichment`

The capability uses Codex-added LCP/MCP data sources and local PericopeAI
metadata to create evidence-backed historical-context drafts. It does not
publish directly. Public author profiles consume only reviewed snapshots.

## Product Outcome

For each public author profile, PericopeAI can show:

- concise historical summary
- period and approximate date range
- relevant places
- timeline of key events
- world context such as empire, school, religious movement, controversy, or
  intellectual tradition
- works chronology when known
- influences received
- contemporaries and peer clusters
- later reception
- provenance, confidence, and review state

This gives the reader context before selecting an author as a counsel lens,
without making live external data sources part of the reader path.

## Non-Goals

- Do not call LCP/MCP data sources from the public author-profile request path.
- Do not publish unreviewed historical claims.
- Do not scrape or copy long-form biographies into profile prose.
- Do not treat Wikidata or any single source as sufficient truth for contested
  claims.
- Do not mutate author-acquisition ledgers.
- Do not claim source-text acquisition, production corpus sync, or public author
  completion.
- Do not add a graph database, deployed service, route, port, or environment
  variable in the first release.

## Relationship To Existing Plans

This capability sits between Source Steward, reference intelligence, and author
profiles.

| Surface | Owns | Boundary |
| --- | --- | --- |
| Source Steward | source discovery, source cards, rights, edition/source quality, acquisition readiness | provides approved source identifiers and source cards |
| Reference Intelligence | evidence spans, references, cross-author relationships, acquisition leads, operator review | can supply influence and reception evidence |
| Author Acquisition | queue state, local text acquisition, indexing, production publication, public verification | may consume historical context during profile release checks |
| Author Historical Context Capability | historical profile claims and reviewed snapshots | enriches author profiles, but does not acquire or publish authors |
| Public Profile API | reader-facing profile payload | serves reviewed snapshot only |

The capability should be developed as a reference-intelligence-adjacent
capability, not as a public chat feature.

## Operating Model

Use the same two-plane model as reference intelligence and author acquisition:

- `fortress.lan` runs bounded background jobs for source pulls, normalization,
  claim extraction, conflict detection, draft generation, and validation.
- `fortress.local` presents operator review queues, evidence packets, approvals,
  edits, rejects, deferrals, and publication approvals.
- `pericopeai.local` verifies local profile behavior.
- `https://pericopeai.com` receives only reviewed snapshots through the existing
  deployment and publication path.

The intended flow is:

```text
Author slug and existing profile metadata
  -> identity resolution
  -> approved LCP/MCP/source-card pulls
  -> evidence-backed historical claims
  -> conflict and confidence scoring
  -> historical context draft
  -> fortress.local operator review
  -> approved snapshot artifact
  -> corpus/profile metadata sync
  -> /api/v1/authors/{slug}/profile
  -> public author profile rendering
```

## Architecture Diagram

The Mermaid source for this capability is
[`author-historical-context-capability-architecture.mmd`](author-historical-context-capability-architecture.mmd).

The diagram shows the full support structure around the agent capability:
operator intent, existing PericopeAI truth, Codex LCP/MCP and Source Steward
inputs, Fortress LAN execution, Fortress Local review, approved snapshot
publication, profile API consumption, and the guardrails that keep live external
data and pending claims out of public author profiles.

## Capability Manifest

The first implementation should define a machine-readable capability registry
entry.

```json
{
  "id": "author_historical_context_enrichment",
  "owner": "reference_intelligence",
  "runtime_plane": "fortress.lan",
  "review_plane": "fortress.local",
  "input_schema": "author_historical_context_request.v1",
  "output_schema": "author_historical_context_draft.v1",
  "allowed_sources": [
    "local_author_catalog",
    "local_author_biographies",
    "local_author_books",
    "source_steward_source_cards",
    "reference_intelligence_edges",
    "wikidata",
    "openlibrary",
    "crossref",
    "openalex",
    "gutenberg"
  ],
  "requires_review": true,
  "may_publish_directly": false,
  "public_runtime_dependency": false
}
```

## Source Registry

Every data source available to the capability needs a source registry record.
The registry should describe what the source can be used for, reliability tier,
rights posture, and whether direct prose may be used.

```json
{
  "source_id": "wikidata",
  "display_name": "Wikidata",
  "kind": "structured_metadata",
  "allowed_for": [
    "identity",
    "aliases",
    "life_dates",
    "places",
    "external_ids"
  ],
  "not_allowed_for": [
    "longform_profile_prose",
    "sole_source_for_contested_claims"
  ],
  "reliability_tier": "supporting",
  "rights_status": "metadata_reuse_reviewed",
  "review_required": true
}
```

Initial source tiers:

| Tier | Examples | Use |
| --- | --- | --- |
| canonical local | author catalog, author books, approved source cards, reviewed reference edges | primary PericopeAI source of truth |
| authority metadata | Wikidata, VIAF or similar IDs when available | identity, dates, aliases, places, external IDs |
| bibliographic metadata | Open Library, Crossref, OpenAlex, Gutenberg catalogs | works, editions, publication metadata, acquisition hints |
| corpus-derived evidence | acquired source text, explicit citations, cross-reference edges | influence, reception, author/work relationships |
| reviewer-authored | operator edits and reviewed notes | final public wording and judgment calls |

## Data Artifacts

Phase 0 should be file-backed and fixture-backed. Later phases can promote to
MySQL tables once the contracts settle.

Recommended local artifacts:

| Artifact | Purpose |
| --- | --- |
| `AugustineCorpus/metadata/author-historical-context.json` | reviewed public snapshots keyed by author slug |
| `AugustineCorpus/metadata/author-historical-context.sources.json` | source registry and source-use policy |
| `AugustineCorpus/metadata/author-historical-context.schema.json` | public snapshot schema |
| `AugustineCorpus/reference_intelligence/historical_context/fixtures/` | deterministic fixture inputs and expected outputs |
| `AugustineCorpus/reference_intelligence/historical_context/runs/` | local dry-run outputs, not committed unless explicitly curated |

Candidate MySQL tables for a later persistent implementation:

- `author_historical_context_runs`
- `author_historical_claims`
- `author_historical_context_drafts`
- `author_historical_context_review_actions`
- `author_historical_context_snapshots`

MySQL remains canonical for deployed application persistence. A graph database
is not required for this capability.

## Input Contract

```json
{
  "request_id": "uuid",
  "author_slug": "augustine",
  "author_name": "Augustine of Hippo",
  "external_ids": {
    "wikidata": "Q8018"
  },
  "scope": [
    "identity",
    "period",
    "places",
    "timeline",
    "world_context",
    "works_chronology",
    "influences",
    "contemporaries",
    "reception"
  ],
  "source_policy": "reviewed-profile-v1",
  "dry_run": true
}
```

## Run Record Contract

```json
{
  "run_id": "uuid",
  "capability": "author_historical_context_enrichment",
  "author_slug": "augustine",
  "profile": "reviewed-profile-v1",
  "status": "completed",
  "started_at": "2026-07-08T00:00:00Z",
  "finished_at": "2026-07-08T00:01:00Z",
  "sources_requested": ["local_author_catalog", "wikidata", "openlibrary"],
  "sources_used": ["local_author_catalog", "wikidata"],
  "counts": {
    "raw_items": 32,
    "claims_created": 18,
    "claims_flagged": 2,
    "draft_sections": 7
  },
  "flags": ["date_precision_review"]
}
```

## Claim Contract

Every publishable historical statement should start as a claim with evidence.

```json
{
  "claim_id": "uuid",
  "author_slug": "augustine",
  "claim_type": "timeline_event",
  "normalized_value": {
    "date_label": "395",
    "title": "Became bishop of Hippo",
    "body": "Augustine entered episcopal leadership in Roman North Africa."
  },
  "source_refs": [
    {
      "source_id": "wikidata",
      "source_record_id": "Q8018",
      "field": "position held",
      "retrieved_at": "2026-07-08T00:00:00Z"
    }
  ],
  "confidence": 0.82,
  "confidence_reason": "Structured authority metadata supports the event, but wording requires review.",
  "review_status": "pending_review",
  "flags": []
}
```

## Draft Contract

```json
{
  "author_slug": "augustine",
  "generated_by_run_id": "uuid",
  "review_status": "pending_review",
  "historical_context": {
    "summary": "Augustine wrote from late Roman North Africa as imperial Christianity, local controversy, and the weakening western empire shaped the questions before him.",
    "period": {
      "label": "Late antiquity",
      "start_year": 354,
      "end_year": 430,
      "precision": "life_dates",
      "claim_ids": ["uuid"]
    },
    "places": [
      {
        "name": "Roman North Africa",
        "role": "primary setting",
        "claim_ids": ["uuid"]
      }
    ],
    "timeline": [
      {
        "date_label": "354",
        "title": "Born in Thagaste",
        "body": "Places Augustine in Roman Numidia.",
        "claim_ids": ["uuid"]
      }
    ],
    "world_context": [
      {
        "label": "late Roman imperial Christianity",
        "body": "The Christian church had public imperial standing but remained shaped by local controversies and pastoral disputes.",
        "claim_ids": ["uuid"]
      }
    ],
    "works_chronology": [],
    "influences": {
      "received_from": [],
      "contemporaries": [],
      "later_reception": []
    }
  },
  "source_refs": [],
  "flags": [],
  "review_required": true
}
```

## Published Snapshot Contract

The public snapshot is the only shape the author profile API should expose.
Pending claims, operator notes, raw source responses, and source credentials are
excluded.

```json
{
  "author_slug": "augustine",
  "version": "2026-07-08.1",
  "review_status": "approved",
  "reviewed_at": "2026-07-08T00:00:00Z",
  "reviewed_by": "operator",
  "historical_context": {
    "summary": "string",
    "period": {},
    "places": [],
    "timeline": [],
    "world_context": [],
    "works_chronology": [],
    "influences": {},
    "reception": []
  },
  "provenance": {
    "source_count": 3,
    "claim_count": 18,
    "confidence": 0.86,
    "generated_by_run_id": "uuid"
  }
}
```

## Agent Components

### 1. Identity Resolver

Responsibilities:

- read the existing author catalog and author profile metadata
- normalize slug, display name, catalog name, aliases, and external IDs
- detect ambiguous or duplicate author identities
- route biblical or composite personas into `traditional`, `critical`, or
  `composite` identity modes

Acceptance:

- acquired authors resolve to a single current slug
- unknown external IDs do not block local-only authors
- ambiguity is surfaced as a review flag, not hidden

### 2. Source Planner

Responsibilities:

- select allowed sources from the source registry
- choose source-specific fields for the requested scope
- avoid live calls when fixture or cached data is requested
- produce a deterministic source plan before pulling data

Acceptance:

- every source pull is explainable by source policy
- source plans can run in dry-run mode
- public-profile generation does not require live external calls

### 3. Source Collector

Responsibilities:

- call allowed LCP/MCP/local providers
- capture retrieval metadata
- normalize responses into source records
- redact secrets, credentials, cookies, and unrelated private data

Acceptance:

- raw source data is stored only in local run artifacts or operator storage
- failures are captured per source and do not fail the whole run unless the
  source is mandatory
- connector outputs are not copied directly into public prose

### 4. Claim Extractor

Responsibilities:

- convert source records into atomic claims
- classify claim type
- preserve source references and field provenance
- assign initial confidence
- mark contested or unsupported claims

Claim types:

- identity
- life_date
- place
- timeline_event
- movement_or_school
- political_context
- religious_context
- work_chronology
- influence_received
- contemporary
- reception
- uncertainty_note

Acceptance:

- every claim has at least one source reference
- contested claims carry flags
- no claim becomes public before review or confidence gating

### 5. Conflict Detector

Responsibilities:

- compare dates, places, identity labels, and work attributions across sources
- flag missing precision
- detect biblical authorship differences
- detect conflict between catalog data and external metadata

Acceptance:

- conflicts appear in the review packet
- confidence is lowered when sources disagree
- the draft preserves uncertainty rather than forcing a single certainty level

### 6. Context Composer

Responsibilities:

- assemble claims into the historical-context schema
- write concise reader-facing prose
- keep interpretation separate from evidence
- avoid long source-derived passages
- preserve claim IDs for review traceability

Acceptance:

- draft text is short enough for profile UX
- every section links back to claims
- generated prose never contains raw citations, URLs, or review notes unless
  they belong in provenance detail

### 7. Influence And Reception Mapper

Responsibilities:

- combine source metadata, corpus references, and reviewed cross-reference edges
- distinguish influence received, contemporary relationship, and later reception
- mark inferential links as lower confidence unless source evidence is explicit

Acceptance:

- no influence edge is published without evidence or review
- outbound and inbound relationships are typed
- reference-intelligence edges remain the preferred source when available

### 8. Review Packet Builder

Responsibilities:

- generate a reviewable bundle for `fortress.local`
- group claims by section
- show source count, confidence, conflicts, and proposed public wording
- produce a diff against the current published snapshot

Acceptance:

- reviewer can approve, reject, edit, defer, or mark a claim as needs-source
- reviewer can approve the whole snapshot only when all public claims are
  approved or confidence-gated
- all review actions are auditable

### 9. Snapshot Publisher

Responsibilities:

- write approved snapshots to the local artifact
- validate schema
- prevent pending or rejected claims from entering public output
- preserve old snapshot version for rollback

Acceptance:

- publication requires explicit review approval
- output validates before write
- public profile tests pass after write

## Operator Review Workflow

Review actions:

- approve claim
- reject claim
- edit public wording
- defer claim
- merge duplicate claim
- mark needs better source
- mark rights concern
- approve snapshot

Every action records:

- actor
- timestamp
- source object ID
- old state
- new state
- reason or note
- run ID

Operator review must answer:

1. Why is this historical claim in the profile?
2. Which source supports it?
3. Is it certain, traditional, critical, or contested?
4. Is the wording safe to publish?
5. Does this belong on the author profile or only in internal context?

## Public API Contract

The existing author profile endpoint should grow additively:

`GET /api/v1/authors/{author_slug}/profile`

Additive field:

```json
{
  "historical_context": {
    "summary": "string",
    "period": {},
    "places": [],
    "timeline": [],
    "world_context": [],
    "works_chronology": [],
    "influences": {},
    "reception": [],
    "provenance": {
      "source_count": 3,
      "claim_count": 18,
      "confidence": 0.86,
      "version": "2026-07-08.1"
    }
  }
}
```

Fallback behavior:

- if no reviewed snapshot exists, omit `historical_context` or return `null`
- do not block profile loads
- do not call external sources from the request path
- do not expose pending review data

## Frontend Rendering Plan

Author profile UI should show historical context as a dense profile section, not
a marketing page.

Recommended layout:

- header remains portrait, name, taxonomy, and summary
- add a compact "Historical Context" section below the profile summary
- show period and places as short metadata rows
- show 3 to 6 timeline items by default with expand affordance
- show world context as short bullets
- show influences/reception as grouped chips or rows
- show provenance as a small "Reviewed sources" detail, not as noisy raw URLs

The UI should remain useful when `historical_context` is missing.

## Implementation Phases

### Phase 0: Contracts And Fixtures

Deliverables:

- this execution plan
- source registry schema draft
- historical context public snapshot schema draft
- fixture author set: `augustine`, `plato`, `paul`, and one contested biblical
  persona
- expected fixture output
- dry-run CLI stub that reads local fixture data only

Exit criteria:

- schema validates fixture outputs
- every fixture claim has source refs
- contested authorship can be represented without false certainty
- no live LCP/MCP calls are required
- no public API changes are made

### Phase 1: Local Source Registry And Source Planner

Deliverables:

- file-backed source registry
- local source-policy loader
- source planner for requested scope
- dry-run report that lists intended source pulls

Exit criteria:

- source use is explicit and reviewable
- disallowed source uses are blocked
- source planner is deterministic for the same author and scope

### Phase 2: Identity Resolution And Source Collection

Deliverables:

- author identity resolver using existing catalog/profile metadata
- local provider adapters for current author catalog, biography, books, and
  author-acquisition ledgers
- optional LCP/MCP provider adapters behind dry-run and cache controls
- normalized source record output

Exit criteria:

- current public authors resolve against local catalog
- missing external IDs are flagged, not fatal
- connector failure produces a partial run with clear source-level errors

### Phase 3: Claim Extraction, Conflict Detection, And Draft Assembly

Deliverables:

- claim extractor for life dates, places, timeline, context, works, influence,
  and reception
- confidence scorer
- conflict detector
- draft composer
- review packet output

Exit criteria:

- draft is fully traceable to claims
- conflicts are visible
- no draft item lacks source refs
- claim confidence changes when source support is weak or conflicting

### Phase 4: Operator Review

Deliverables:

- review packet format
- local review action records
- approve/reject/edit/defer flow
- diff against current snapshot
- audit trail

Exit criteria:

- reviewer can approve a complete historical context for one author
- rejected claims do not appear in approved snapshot
- edited wording remains linked to source claims
- review actions are reproducible from local artifacts or MySQL

### Phase 5: Snapshot Publication And API Exposure

Deliverables:

- reviewed snapshot writer
- schema validation
- merge into author profile loader
- additive `/api/v1/authors/{slug}/profile` contract update
- API tests for missing, pending, and approved historical context

Exit criteria:

- approved snapshot appears in local profile endpoint
- pending data remains hidden
- author profile endpoint still works when snapshot is missing
- public profile verifier can be extended without requiring every author to
  have historical context on day one

### Phase 6: Frontend Profile Rendering

Deliverables:

- author profile historical context section
- missing-data fallback
- compact provenance display
- responsive timeline layout

Exit criteria:

- profile remains readable on desktop and mobile
- no text overlap
- no profile route depends on live external data
- historical section does not crowd out chat entry points

### Phase 7: Backfill And Scale

Deliverables:

- batch runner for selected author slugs
- priority order for author backfill
- operator backlog view
- confidence and coverage dashboard

Initial backfill priority:

1. flagship non-biblical authors already public: Augustine, Plato, Freud,
   Marcus Aurelius, Irenaeus, John Chrysostom
2. economic-theorist queue once public verification gates are satisfied
3. biblical author/persona profiles with contested-authorship handling
4. remaining public author catalog

Exit criteria:

- batch runs are resumable
- review queue remains bounded
- public profiles can ship incrementally

## CLI Shape

Initial local commands:

```bash
author-historical-context plan --author augustine --scope full
author-historical-context gather --author augustine --dry-run
author-historical-context draft --author augustine --from-fixtures
author-historical-context review-packet --run-id <run_id>
author-historical-context publish --author augustine --approved-review-id <review_id>
author-historical-context validate --author augustine
```

The `publish` command must fail unless an approved review record exists.

## Validation Rules

Public snapshot validation:

- `author_slug` exists in author catalog
- `review_status` is `approved`
- no pending, rejected, or deferred claims are included
- every timeline item has at least one approved claim
- every source ref points to a registered source
- all source refs have retrieval or local artifact metadata
- confidence is numeric and bounded between 0 and 1
- contested or composite authorship is explicitly labeled
- no source text is copied into long-form prose
- no raw private prompts, cookies, bearer tokens, API keys, or operator-only
  notes appear in public output
- schema remains additive for `/api/v1/authors/{slug}/profile`

## Testing Plan

Required tests:

- source registry schema tests
- source policy allow/deny tests
- identity resolver tests
- fixture extraction tests
- evidence/source-ref tests
- conflict detection tests
- confidence scoring tests
- contested authorship tests
- review action tests
- snapshot writer tests
- public visibility tests
- author profile API contract tests
- frontend fallback tests
- dry-run command tests

Tests should prove that chat and profile loading still work when historical
context is unavailable.

## Observability

Track:

- runs started, completed, failed, and cancelled
- source pulls attempted and failed
- claims created by type
- conflicts by type
- claims approved, rejected, deferred, and edited
- average confidence by author
- snapshot publish count
- profile coverage by public author
- validation failures
- review backlog size

Logs must not include credentials, cookies, authorization headers, private
prompts, or unrelated user data.

## Risk Controls

| Risk | Control |
| --- | --- |
| External source is wrong or incomplete | require source refs, confidence, conflict detection, and review |
| Agent writes polished but unsupported prose | require every public sentence to trace to approved claims |
| Contested authorship is flattened | represent traditional, critical, composite, and uncertain modes |
| Public profile becomes slow | serve local reviewed snapshot only |
| Rights risk from copied biographies | prohibit long-form source copying and review public wording |
| Capability drifts into author acquisition | block ledger writes and source-text acquisition |
| Review queue grows without limit | batch by priority and expose backlog metrics |
| Schema churn breaks frontend | additive API field with missing-data fallback |

## Security And Privacy

- LCP/MCP connector credentials remain outside public artifacts.
- Raw connector responses stay local/operator-only.
- Public snapshots include only reviewed facts and compact provenance.
- Operator notes are excluded from public output.
- Logs contain IDs, counts, timings, and failure classes, not prompt bodies or
  secrets.
- Any future operator API must enforce authentication, authorization, rate
  limits, and scope limits.

## Definition Of Done

The first complete release is done when:

- one flagship author can run through plan, gather, draft, review, publish, and
  validate locally
- every public historical-context item traces to source-backed claims
- conflicts and uncertain authorship are represented safely
- approved snapshot appears in `/api/v1/authors/{slug}/profile`
- missing historical context does not break profiles
- frontend displays the section without layout regressions
- public verifier or API tests confirm approved data is visible and pending data
  is hidden
- deployed architecture and deployment locks still confirm no new public route,
  service, port, or environment variable was introduced

## First Buildable Slice

Start with Augustine only.

Scope:

- use existing author catalog, biography, books, portrait metadata, and local
  source-card fixtures
- optionally use Wikidata only through a cached or fixture-backed adapter
- produce period, places, 5 timeline items, world context, works chronology,
  and 3 influence/reception rows
- generate a review packet
- manually approve the snapshot
- expose it through local profile payload

Do not start with global backfill, frontend polish, or live external-provider
dependency. The first slice should prove the contracts and review gates.
