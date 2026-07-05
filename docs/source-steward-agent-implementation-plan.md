# Source Steward Agent Implementation Plan

Status: planned, not deployed
Owner surface: PericopeAI source and provenance layer
Primary planning source: `/Users/benjaminlagrone/Documents/projects/.workspace/proposals/dataset-integrations-2026-06-26/pericopeai.md`

## Purpose

The Source Steward Agent maintains trusted source intelligence for PericopeAI
and the Solomonic Clock. It discovers candidate works, normalizes source
metadata, prepares rights-gated ingestion proposals, and publishes approved
source cards and clock anchors.

The agent is not a public chat persona. It is an internal stewardship workflow
that improves the evidence layer behind counsel, citations, source pages, and
clock-guided PericopeAI sessions.

## Current Runtime Boundaries

The first implementation must fit the deployed PericopeAI shape:

- `augustine-corpus-live` owns retrieval, author indexes, book lookup, and LLM
  generation.
- `pericopeai-api` owns chat/session handling, citations, source persistence,
  and segmented chat responses under `/api/v2/chat`.
- `solomonic-clock` owns clock-derived context, source reference selection,
  guided prompt generation, and clock context bundles.
- PericopeAI owns final answer generation and retrieval grounding.
- The clock must not implement Pericope chat or author behavior.
- PericopeAI must not reimplement the clock's symbolic selection logic.

This plan does not add a production service, hostname, route, port, environment
variable, or deployment path. If the agent later becomes a daemon or deployable
service, update the deployed architecture, workspace deployment lock, compose
contract, and smoke checks in the same change.

## Agent Mission

Find, evaluate, normalize, and propose source material for PericopeAI, then
create source-backed anchors that the Solomonic Clock can use without making
live third-party dataset calls from public render paths.

## Operating Loop

```text
requested work or scheduled backlog item
  -> discover source candidates
  -> normalize candidate metadata
  -> rank confidence and rights risk
  -> prepare ingestion proposal
  -> wait for human approval
  -> ingest approved metadata and text
  -> rebuild or refresh corpus index
  -> verify /v1/context provenance metadata
  -> publish source cards
  -> publish Solomonic Clock source anchors
```

## Non-Goals

- No autonomous full-text ingestion.
- No automatic publication of uncertain editions, translations, or images.
- No live Gutendex, Open Library, Crossref, OpenAlex, Wikimedia Commons, or
  Hugging Face calls from public chat or clock render paths.
- No Sysco or private enterprise data in the public PericopeAI or Solomonic
  Clock stack.
- No new production service until deployment governance is updated.

## Provider Responsibilities

| Provider | Role | First use | Guardrail |
| --- | --- | --- | --- |
| Gutendex / Project Gutenberg | Public-domain text discovery | Candidate work and text URL lookup | Public-domain status still requires edition review. |
| Open Library | Work, edition, author, scan, cover, and publication metadata | Work/edition resolver | Scan availability is not reuse permission. |
| Crossref | DOI and scholarship metadata | Secondary source cards | Abstracts and full text may be copyrighted. |
| OpenAlex | Citation graph, related works, topics, OA status | Scholarly context panel | OA status must be checked per work. |
| Wikimedia Commons | Portraits, manuscripts, maps, and visual enrichment | Source-page and author media | File-level license and attribution required. |
| Hugging Face datasets | Corpus discovery | Candidate leads only | Dataset provenance and license review required. |
| SEC EDGAR Full-Text Search | Search UX reference | Pattern reference only | Not a theological source corpus. |

## Human Gates

The agent may write candidate records and draft proposals, but human approval
is required before:

- importing full text into corpus folders
- marking a source as approved for public use
- replacing an existing source edition
- publishing attribution-required images
- using modern translations or uncertain copyright material
- adding a new deployable runtime surface

## Data Contracts

### Source Candidate

`source_candidate` is the agent's normalized discovery output. It is metadata
only.

```json
{
  "candidate_id": "gutendex:123",
  "source": "gutendex",
  "source_id": "123",
  "query": "augustine confessions",
  "title": "Confessions",
  "authors": ["Augustine"],
  "year": 1887,
  "languages": ["en"],
  "formats": ["text/plain", "text/html"],
  "access_url": "https://...",
  "source_url": "https://...",
  "rights_note": "Public-domain status requires edition review.",
  "confidence": 0.91,
  "created_at": "2026-07-04T00:00:00Z"
}
```

### Review Record

`review_record` captures the rights and edition decision. It can approve
metadata while still rejecting full-text ingestion.

```json
{
  "candidate_id": "gutendex:123",
  "status": "needs_review",
  "approved_for_metadata": true,
  "approved_for_full_text": false,
  "edition": "",
  "translator": "",
  "license": "",
  "rights_note": "Need translator and publication-year confirmation.",
  "reviewer": "",
  "reviewed_at": ""
}
```

### Ingestion Proposal

`ingestion_proposal` is the agent's handoff package for a human reviewer.

```json
{
  "proposal_id": "source-proposal-augustine-confessions-20260704",
  "work_key": "augustine/confessions",
  "recommended_candidate_id": "gutendex:123",
  "alternates": ["openlibrary:works/OL..."],
  "risk_level": "medium",
  "recommended_action": "approve_metadata_only",
  "notes": [
    "Confirm translator before full-text ingestion.",
    "Prefer public-domain edition with stable plain-text URL."
  ]
}
```

### Approved Source Card

`source_card` is the compact provenance object returned through PericopeAI and
clock context surfaces after approval.

```json
{
  "source_id": "pericope:augustine:confessions:gutenberg-123",
  "work": "Confessions",
  "title": "Confessions",
  "authors": ["Augustine"],
  "edition": "reviewed public-domain edition",
  "translator": "",
  "language": "en",
  "source": "gutendex",
  "source_url": "https://...",
  "rights_note": "Approved for public metadata display.",
  "approval_status": "metadata_approved",
  "accessed_at": "2026-07-04"
}
```

### Clock Anchor

`clock_anchor` binds approved source cards to clock references. It is consumed
by the Solomonic Clock and may be passed into PericopeAI as `clock_context`.

```json
{
  "anchor_id": "clock:wisdom:proverbs-3-5",
  "reference": "Proverbs 3:5",
  "source_id": "pericope:solomon:proverbs:approved",
  "display_label": "Proverbs 3:5",
  "rights_note": "Reviewed public-domain text.",
  "clock_binding": {
    "kind": "wisdom",
    "use": "daily_guidance"
  }
}
```

## Proposed File Ownership

### AugustineCorpus

First implementation:

- `AugustineCorpus/source_steward/`
  - resolver contracts
  - provider adapters
  - ranking and rights-risk helpers
- `AugustineCorpus/tools/source_steward.py`
  - local CLI entrypoint
- `AugustineCorpus/texts/_source_candidates/`
  - generated candidate and proposal JSON files for review

Existing corpus ingestion should be extended, not replaced. Approved
provenance fields should flow through `book_metadata.json` and then through
the existing `/v1/context` metadata contract.

### AugustineService

First implementation:

- preserve `/api/v2/chat` compatibility
- keep retrieval grounding in AugustineCorpus
- enrich citation payloads with approved source-card metadata
- persist compact source metadata through the existing session, citation, and
  reference paths

No new public endpoint is required in the first slice.

### AugustineFE

First implementation:

- render source cards inside existing citation/reference UI
- distinguish approved corpus text from metadata-only candidate information
- avoid showing raw candidate records as if they were approved citations

### Solomonic_Seals

First implementation:

- add a curated source-anchor data file, for example
  `Solomonic_Seals/data/source_anchors.json`
- enrich `/api/clock/context`, `/api/clock/content-bundle`, and
  `/api/clock/wisdom-anchor` with approved `source_cards`
- pass compact `source_cards` through the existing clock-to-Pericope `ctx`
  launch payload

The clock should continue to resolve scripture/support text from PericopeAI
first when configured to do so, with file fallback for local resilience.

## Phased Implementation

### Phase 0: Contract And Fixtures

Deliverables:

- define `source_candidate`, `review_record`, `ingestion_proposal`,
  `source_card`, and `clock_anchor` JSON schemas
- add static test fixtures for Gutendex and Open Library responses
- add fixture-based unit tests with no network dependency

Acceptance:

- contracts validate sample Augustine, Plato, Aristotle, Proverbs, and Psalms
  candidates
- fixtures run in CI/local test without third-party network access

### Phase 1: Metadata-Only Resolver

Deliverables:

- Gutendex adapter
- Open Library adapter
- resolver CLI:

```bash
python -m source_steward resolve "augustine confessions"
python -m source_steward resolve "plato republic"
python -m source_steward resolve "solomon proverbs"
```

Acceptance:

- resolver returns ranked candidates for Augustine, Aquinas, Plato, Aristotle,
  Solomon, Proverbs, and Psalms
- each candidate includes source URL, access URL, rights warning, and
  confidence score
- no full text is downloaded into live corpus folders

### Phase 2: Review And Proposal Workflow

Deliverables:

- generated proposal files under `_source_candidates/`
- rights-risk labels:
  - `metadata_only`
  - `public_domain_candidate`
  - `translation_uncertain`
  - `copyright_risk`
  - `attribution_required`
- reviewer status fields

Acceptance:

- a reviewer can approve metadata without approving full-text ingestion
- rejected or uncertain sources remain discoverable but cannot enter the
  approved corpus path

### Phase 3: Corpus Metadata Extension

Deliverables:

- extend `book_metadata.json` entries with:
  - `source_id`
  - `source_url`
  - `edition`
  - `translator`
  - `license`
  - `rights_note`
  - `approval_status`
  - `accessed_at`
- pass approved fields through `preprocess_and_index.py`
- ensure `/v1/context` returns the fields as additive metadata

Acceptance:

- existing metadata fields remain backward compatible
- `/v1/context` still returns `book`, `work`, `source`, `chapter`,
  `position`, `verse`, and `reference`
- approved source-card fields appear when available

### Phase 4: PericopeAI Source Cards

Deliverables:

- map retrieval metadata into compact source-card payloads
- persist source card data with assistant citations where appropriate
- render source cards in the web UI

Acceptance:

- counsel answers can show work, edition, source URL, and rights note
- source-card display does not alter author persona or answer grounding
- metadata-only candidates are never displayed as approved retrieval citations

### Phase 5: Solomonic Clock Anchors

Deliverables:

- curated `source_anchors.json`
- clock resolver for approved anchors
- `source_cards` added to clock context/content-bundle/wisdom-anchor payloads
- compact source cards included in the existing Pericope launch `ctx`

Acceptance:

- clock context can identify the approved source behind a Psalm, Proverb, or
  wisdom reference
- PericopeAI stores the clock source context as structured session metadata
- public clock rendering does not depend on third-party source APIs

### Phase 6: Secondary Scholarship Context

Deliverables:

- Crossref adapter
- OpenAlex adapter
- secondary scholarship source-card type
- related works panel or study context payload

Acceptance:

- DOI/citation graph metadata appears as secondary context only
- secondary literature is clearly separated from primary corpus grounding
- copyright warnings remain visible for abstracts/full text

### Phase 7: Media Enrichment

Deliverables:

- Wikimedia Commons adapter
- file-level license and attribution capture
- approved media card schema
- UI/source page rendering rules for attribution

Acceptance:

- attribution-required media is not published without visible attribution
- public-domain media can be displayed with source metadata
- author/source pages can distinguish portrait, manuscript, and map assets

### Phase 8: Background Agent Runtime

Only start this phase after the CLI and approval workflow are proven.

Deliverables:

- scheduled local/background job design
- lock and idempotency model
- operational logs with no prompt bodies or private content
- deployment contract updates if promoted beyond local execution

Acceptance:

- the agent can refresh candidate metadata without modifying approved corpus
  text automatically
- failures are visible through sanitized logs
- deployment docs, locks, compose files, and smoke checks are updated before
  any production daemon exists

## Test Plan

- Unit tests for provider response normalization.
- Schema tests for all candidate/proposal/source-card/anchor contracts.
- Fixture tests for rights-risk labeling.
- Corpus tests proving metadata fields pass through index build and
  `/v1/context`.
- API tests proving `/api/v2/chat` remains backward compatible while returning
  source-card payloads when available.
- UI tests for citation/source-card rendering.
- Clock tests proving `source_cards` appear in context payloads and survive
  Pericope launch `ctx` encoding.
- Regression tests proving no public request path calls third-party dataset APIs.

## Observability

The agent should emit sanitized counters and phase timings:

- candidates discovered
- candidates by provider
- candidates by risk label
- proposals created
- proposals approved/rejected
- source cards published
- clock anchors published
- provider API failures
- resolver latency by provider

Logs must not contain API keys, bearer tokens, user prompts, private notes, or
unreviewed full text.

## Success Metrics

- Percentage of corpus works with approved source-card metadata.
- Percentage of PericopeAI answer citations that include source provenance.
- Number of clock wisdom/scripture anchors backed by approved source cards.
- Time from requested work to metadata proposal.
- Time from approval to verified `/v1/context` metadata.
- Zero public render/chat requests blocked on third-party dataset APIs.

## First Build Slice

Implement the smallest useful version:

1. Add the Source Steward contracts and fixture tests.
2. Add Gutendex and Open Library metadata-only adapters.
3. Add a local resolver CLI for `augustine confessions`,
   `plato republic`, and `solomon proverbs`.
4. Write candidate/proposal JSON files under an isolated review folder.
5. Extend one approved `book_metadata.json` record with source-card fields.
6. Verify `/v1/context` returns the additive provenance fields.
7. Add one Solomonic Clock source anchor and verify it appears in
   `/api/clock/content-bundle`.

This first slice should not add a new deployable service.
