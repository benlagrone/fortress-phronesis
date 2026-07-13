# Reference Intelligence Agents Implementation Plan

**Status:** planned
**Owner surface:** Fortress Phronesis docs and deployment control plane
**Runtime target:** Fortress LAN background jobs with local operator review
**Current deployed source of truth:** MySQL plus the existing author-acquisition ledgers
**Deployment note:** This plan does not add a deployed service, public route, host port, environment variable, or graph database by itself.

## Purpose

This document plans the PericopeAI reference-intelligence agent system, excluding
the Source Steward Agent.

The goal is to turn references into durable product infrastructure:

- citations and named references extracted from acquired or approved corpus
  material
- evidence-backed cross-references between passages, authors, works, and
  scripture
- non-acquired author/work discovery
- acquisition leads that explain why an author belongs in the queue
- reviewed reference intelligence that can appear in PericopeAI without exposing
  internal graph topology or unreviewed acquisition leads

## Explicit Exclusion: Source Steward Agent

The Source Steward Agent is out of scope for this plan.

Source Steward owns:

- source candidate discovery
- source metadata normalization
- rights and edition review proposals
- approved source cards
- clock anchors
- provider adapters for source acquisition readiness
- full-text ingestion proposals

This plan may consume approved source-card metadata or source identifiers from
Source Steward, but it must not duplicate Source Steward's rights, edition,
media, or source-ingestion responsibilities.

## Operating Model

Use a two-plane workflow:

- `fortress.lan` runs bounded background jobs for extraction, resolution,
  edge-building, scoring, and lead generation.
- `fortress.local` presents review inboxes, run status, approvals, rejects,
  deferrals, merges, and acquisition handoff proposals.
- `pericopeai.local` and the public PericopeAI application consume only
  reviewed or confidence-gated reference outputs.

The intended flow is:

```text
Acquired corpus and approved metadata
  -> fortress.lan reference-intelligence jobs
  -> resolved references
  -> cross-reference edges
  -> non-acquired author/work leads
  -> fortress.local review
  -> approved acquisition handoff or reader-facing reference data
```

The workflow is operator-assisted. It does not silently acquire authors, publish
authors, ingest third-party text, or modify production acquisition state.

## Agents Covered

| Agent | Owns | Main output |
| --- | --- | --- |
| Run Orchestrator | bounded job execution, idempotency, run status | extraction/build run records |
| Citations Agent | citation/reference extraction and evidence spans | resolved-reference candidates |
| Reference Resolver | canonical author/work/passage/scripture identities | normalized target IDs and status |
| Cross-Reference Agent | typed relationships between references | cross-reference edges |
| Author Discovery Agent | non-acquired author/work lead creation | author discovery leads |
| Acquisition Handoff Agent | approved lead export and ledger dry-run diffs | acquisition queue proposals |
| Operator Review Agent | review states, audit trail, local control-plane UX | approvals, rejects, deferrals, merges |
| Reader Reference Adapter | reviewed outputs for PericopeAI API/UI | related references and provenance payloads |

## Guardrail Summary

- No durable reference without evidence and provenance.
- No cross-reference edge without a supporting reference.
- No acquisition lead without supporting reference IDs.
- No acquisition ledger mutation without explicit approval.
- No production publication outside `docs/author-acquisition-process.md`.
- No public endpoint, host port, or deployment path without deployment-lock
  updates.
- No graph database promotion without a separate architecture decision.
- No Source Steward scope inside these agents.

## Roadmap Placement And Independent-Build Boundary

This work belongs in the main PericopeAI roadmap under `v1.3.x`
Cross-Reference Intelligence:

- `v1.3.2` covers reference inference across Bible and non-Bible corpora.
- `v1.3.3` covers the boundary between private graph/reference infrastructure
  and public evidence surfaces.
- `v1.3.4` covers the text-first construction pipeline for explicit reference
  edges and semantic related passages.

It can still be built independently if the early releases remain local,
dry-run, additive, and non-public. The independent-build boundary ends when the
work introduces any of the following:

- production database migrations
- public API endpoints
- reader-facing UI
- scheduled `fortress.lan` runtime
- `fortress.local` operator routes backed by mutable state
- author-acquisition ledger writes
- graph database service, new Docker service, host port, or environment
  variable

At that point, the work must rejoin the locked PericopeAI deployment path:
Fortress Phronesis compose/docs, workspace deployment lock, architecture docs,
and smoke checks must update together.

## Execution Model: Structure, Capability, Agent

Architecture diagram: [Reference Intelligence Agents Architecture](reference-intelligence-agents-architecture.mmd).

Build in this order:

```text
structure -> capability primitives -> dry-run reports -> agent orchestration -> operator review -> reader-facing integration
```

### Structure Work

Structure work defines the durable shape of the system before the system starts
acting.

Deliverables:

- record contracts
- fixture corpus snippets
- review-state vocabulary
- target-status vocabulary
- evidence-span rules
- run/idempotency model
- acquisition-handoff boundaries
- validation tests

Exit gate:

- fixture-backed tests prove references, resolutions, edges, and leads can be
  represented without writing to the live database, acquisition ledgers, public
  APIs, or UI.

### Capability Work

Capability work creates deterministic functions and command-line tools. These
are reusable primitives, not autonomous agents.

Deliverables:

- extractor capability
- resolver capability
- edge-builder capability
- author-lead capability
- handoff dry-run capability
- report writer
- validation commands

Exit gate:

- the same fixture input produces deterministic JSON output, and the output can
  be validated without side effects.

### Agent Work

Agent work orchestrates the capabilities with bounded scope, review states,
operator approval, and retry/failure behavior.

Deliverables:

- run orchestration
- job status and audit records
- review queue generation
- approval/reject/defer actions
- acquisition handoff proposals
- reader-facing adapter after review gates pass

Exit gate:

- an operator can see what happened, why an item was recommended, what evidence
  supports it, and what action is safe to take next.

## Release Train

### Release 0: Planning Hygiene And Worktree Isolation

Goal: prevent documentation, ledger edits, and implementation work from
colliding.

Tasks:

- keep this plan separate from author-acquisition ledger edits
- keep Source Steward work in its own plan
- keep reference-intelligence code separate from author-acquisition execution
  code until the handoff contract is ready
- decide whether first code lives in a local utility package, a tracked script,
  or the owning service repo
- if a tracked script is added under `scripts/`, update `.gitignore` because
  this repo currently ignores `scripts/*` except explicit allow-listed files

Artifacts:

- clean planning diff
- explicit first-slice implementation path
- no changes to `docs/author_acquisition.json`

Exit gate:

- `git diff --check` passes
- planning docs are reviewable without ledger or runtime changes

### Release 1: Contracts And Fixtures

Goal: prove the data model before building behavior.

Tasks:

- define JSON schemas or typed Python dataclasses for:
  - `reference_job_run`
  - `resolved_reference`
  - `reference_resolution`
  - `cross_reference_edge`
  - `author_discovery_lead`
  - `operator_review_action`
  - `acquisition_handoff_proposal`
- create fixture passages for:
  - scripture reference
  - author mention
  - work mention
  - direct quotation
  - weak allusion
  - ambiguous name
  - false positive
  - non-acquired author reference
- create expected-output fixture JSON
- add validation helpers for evidence offsets and required provenance fields

Recommended local shape:

```text
tests/fixtures/reference_intel/
  passages.json
  expected_references.json
  expected_resolutions.json
  expected_edges.json
  expected_author_leads.json
tests/test_reference_intel_contracts.py
```

Acceptance:

- fixtures validate without network access
- every expected reference has evidence offsets
- ambiguous/weak references are marked `pending_review`
- no acquisition ledgers are read for mutation or written

### Release 2: Dry-Run Capability CLI

Goal: run the full fixture pipeline with no side effects.

Tasks:

- build a local CLI entrypoint with dry-run-only behavior
- implement `scan --fixture <name>` first
- implement report output as JSON
- add a `--fail-on-ledger-write` or equivalent safety check if the tool opens
  ledger paths
- add deterministic run IDs for tests

Initial command shape:

```bash
reference-intel scan --fixture augustine-basic --dry-run
reference-intel validate --report tmp/reference-intel/report.json
```

Acceptance:

- CLI emits `reference_job_run`, references, resolutions, edges, leads, and
  summary counts in one JSON report
- running twice produces stable output
- no database, ledger, service, or UI state changes

### Release 3: Citations And Resolver Capability

Goal: extract and resolve references from real local corpus snippets.

Tasks:

- implement scripture detector
- implement author-name detector
- implement work-title detector
- implement quotation marker detection
- implement internal author/work resolver
- implement target status resolver against read-only acquisition ledgers
- implement confidence and reason fields
- add false-positive filters for ambiguous names and work titles

Acceptance:

- known acquired authors resolve to existing slugs
- queued/rejected/non-acquired statuses are distinct
- ambiguous references remain pending review
- source evidence is preserved for every extracted reference

### Release 4: Cross-Reference And Lead Capability

Goal: create relationship edges and author leads from resolved references.

Tasks:

- implement edge builder from reviewed or confidence-gated references
- implement edge invalidation when supporting references change
- implement reverse lookup by author, work, passage, and scripture
- implement non-acquired author lead builder
- implement dedupe/merge rules for lead candidates
- implement initial priority scoring
- implement suppression for rejected/deferred leads

Acceptance:

- every edge points to a supporting reference
- every lead points to supporting references and/or edges
- duplicate leads collapse deterministically
- no lead writes to acquisition ledgers

### Release 5: Local Persistence Prototype

Goal: decide whether the first durable store should be JSON artifacts,
operator-local SQLite, or PericopeAI MySQL tables.

Recommended sequence:

1. JSON report artifacts for fixtures and local dry runs.
2. SQLite or file-backed review state for operator prototype, if needed.
3. MySQL tables only after contracts and review UX are stable.

Tasks:

- define persistence adapter interface
- implement JSON artifact adapter first
- add idempotency keys
- add run status records
- add review status transitions
- add export/import for review records

Acceptance:

- persistence can be wiped and rebuilt from source fixtures/runs
- review state is auditable
- no production database migration is required

### Release 6: Agent Orchestration

Goal: wrap capabilities in bounded, inspectable jobs.

Tasks:

- implement run orchestrator
- add job scope validation
- add per-scope lock
- add retry/cancel/resume behavior
- add sanitized run logs
- add run summary counts
- add failure packets for review

Acceptance:

- failed jobs do not create approved outputs
- cancelled jobs are visible and resumable
- job logs do not leak prompts, secrets, tokens, cookies, or private notes

### Release 7: Operator Review MVP

Goal: make the workflow usable through a local operator surface.

Tasks:

- choose owner surface for the first UI: `local_tools`, `fortress-lan`, or a
  Pericope-specific operator panel
- expose pending references
- expose candidate edges
- expose author leads
- add approve/reject/defer/merge actions
- add review audit trail
- add run history and failure detail

Acceptance:

- owner can answer why a reference or author was recommended
- every action records actor, timestamp, old state, new state, and note
- UI cannot publish authors or write ledgers directly

### Release 8: Acquisition Handoff

Goal: let approved leads become safe acquisition proposals.

Tasks:

- implement handoff dry-run generator
- compare both acquisition ledgers
- detect drift before proposing changes
- prevent duplicate author entries
- generate status strings aligned to `docs/author-acquisition-process.md`
- validate JSON output
- produce a human-review packet

Acceptance:

- approved lead produces a dry-run diff only
- both ledgers remain synchronized
- invalid JSON blocks the proposal
- no status claims production completion before public verification

### Release 9: Reader Reference Adapter

Goal: expose reviewed reference intelligence inside PericopeAI without creating
runtime fragility.

Tasks:

- define reviewed related-reference response shape
- add adapter over reviewed references and edges
- add fallback when reference intelligence is unavailable
- add provenance detail payload
- add UI display rules for related passages/authors/works
- hide pending/rejected leads from normal users

Acceptance:

- chat works if the reference layer is down
- users see evidence snippets and provenance
- raw graph topology and acquisition leads remain hidden

### Release 10: Promotion To Runtime, If Needed

Goal: promote proven local capabilities into durable runtime only after the
local/operator flow works.

Promotion requires:

- explicit decision on persistence
- architecture doc update
- workspace deployment lock update if services, env vars, ports, volumes, or
  public routes change
- smoke checks
- rollback procedure
- data rebuild procedure
- privacy review for any public/user-facing endpoint

Acceptance:

- deployment lock and architecture docs match the implementation
- smoke checks pass
- disabling reference intelligence leaves chat functional

## Work Package Breakdown

| ID | Track | Work package | Depends on | Done when |
| --- | --- | --- | --- | --- |
| RI-001 | Structure | Contract schemas and vocabularies | none | schemas validate fixture records |
| RI-002 | Structure | Fixture passages and expected outputs | RI-001 | fixture tests pass offline |
| RI-003 | Structure | Evidence-offset validator | RI-001 | bad offsets fail tests |
| RI-004 | Capability | Dry-run CLI report | RI-001, RI-002 | stable JSON report emits |
| RI-005 | Capability | Deterministic extractors | RI-002 | scripture/author/work fixtures pass |
| RI-006 | Capability | Resolver against catalogs and ledgers | RI-005 | statuses resolve correctly |
| RI-007 | Capability | Edge builder | RI-006 | every edge has support |
| RI-008 | Capability | Lead builder and dedupe | RI-007 | non-acquired leads explain support |
| RI-009 | Capability | Handoff dry-run | RI-008 | ledger proposal validates without writes |
| RI-010 | Agent | Run orchestrator | RI-004 | scoped jobs are idempotent |
| RI-011 | Agent | Review state machine | RI-010 | approve/reject/defer audited |
| RI-012 | Agent | Operator review MVP | RI-011 | owner can review pending records |
| RI-013 | Integration | Reader adapter | RI-007, RI-011 | reviewed references render safely |
| RI-014 | Ops | Runtime promotion packet | RI-010, RI-012 | deployment changes are gated |

## Conflict Matrix

| Potential conflict | Risk | Avoidance rule |
| --- | --- | --- |
| Source Steward overlap | duplicate rights/source workflows | consume approved source cards only; do not do rights or edition approval here |
| Author acquisition ledger edits | queue drift or invalid JSON | dry-run only until explicit approval; validate both ledgers together |
| Main chat latency | slower user responses | keep extraction jobs off the live chat path |
| Public graph exposure | leaking internal topology | expose evidence summaries, not raw graph structures |
| Deployment lock drift | undocumented service/port/env changes | no runtime promotion without lock, docs, and smoke updates |
| Existing v1.3 surfaces | duplicated reference APIs | start as local adapter; merge into existing references contract only after review |
| Worktree churn | unrelated docs/ledger/scripts mixed together | split planning, ledger changes, and code into separate commits/PRs |

## First Sprint Backlog

The first sprint should stop before persistence, UI, or ledger writes.

1. Add contract schemas or dataclasses for the seven core records.
2. Add fixture passages and expected outputs under `tests/fixtures/reference_intel/`.
3. Add evidence-offset validator tests.
4. Add a dry-run report shape that includes references, resolutions, edges,
   leads, and summary counts.
5. Add a minimal CLI or test helper that runs fixtures only.
6. Add a safety assertion that no acquisition ledger files are modified.
7. Run `git diff --check` and the new fixture tests.

First sprint exit criteria:

- no runtime services added
- no public endpoints added
- no acquisition ledger writes
- no database migration
- fixture pipeline produces deterministic output

## Agent 1: Run Orchestrator

### Mission

Run reference-intelligence jobs safely on bounded scopes and keep the workflow
reproducible.

### Inputs

- author slug
- work ID
- passage range
- corpus version
- extraction profile
- resolver profile
- optional previous run ID for incremental refresh

### Responsibilities

- create run records
- compute idempotency keys
- lock a scope while a job is active
- split large scopes into batches
- track status, timings, counts, failures, and retries
- support cancellation and resume
- prevent partial approved-state writes during failed runs

### Data Contract: `reference_job_run`

```json
{
  "run_id": "uuid",
  "job_type": "citation_scan",
  "scope_type": "author",
  "scope_value": "augustine",
  "corpus_version": "2026-07-05",
  "profile": "default-v1",
  "status": "running",
  "started_at": "2026-07-05T00:00:00Z",
  "finished_at": null,
  "counts": {
    "passages_seen": 1200,
    "references_created": 0,
    "errors": 0
  }
}
```

### Acceptance

- rerunning the same completed scope does not duplicate records
- failed runs can be retried
- cancelled runs are visible and do not create approved outputs
- run logs do not contain prompts, secrets, or raw private user data

## Agent 2: Citations Agent

### Mission

Extract references from acquired or approved corpus text and preserve the exact
source evidence.

### Inputs

- normalized passages
- work metadata
- author catalog
- scripture dictionary
- canonical work-title dictionary
- approved source-card metadata when available

### Responsibilities

- detect explicit citations
- detect named author references
- detect named work references
- detect scripture references
- detect quoted text markers
- identify likely allusions as low-confidence candidates
- capture source offsets and evidence snippets
- classify extraction method
- assign confidence
- avoid resolving ambiguous names too aggressively

### Data Contract: `resolved_reference`

```json
{
  "reference_id": "uuid",
  "run_id": "uuid",
  "source_passage_id": "augustine/confessions/8/12",
  "source_author_slug": "augustine",
  "source_work_id": "confessions",
  "reference_type": "author_mention",
  "raw_text": "Cicero",
  "evidence_start": 184,
  "evidence_end": 190,
  "evidence_text": "Cicero",
  "extraction_method": "catalog_match",
  "confidence": 0.84,
  "review_status": "pending_review",
  "created_at": "2026-07-05T00:00:00Z"
}
```

### Acceptance

- every reference points to a source passage
- every reference has raw text and source evidence offsets
- ambiguous references stay in review instead of becoming durable truth
- extraction does not mutate acquisition ledgers or public UI state

## Agent 3: Reference Resolver

### Mission

Turn raw references into stable identities and status labels.

### Inputs

- `resolved_reference` candidates
- internal author catalog
- internal work catalog
- passage and scripture normalization tables
- acquisition ledgers
- approved source identifiers
- external identifiers from metadata sources when already available

### Responsibilities

- normalize target author, work, passage, or scripture identity
- classify targets as `acquired`, `queued`, `rejected`, `non_acquired`, or
  `unknown`
- dedupe spelling variants and aliases
- detect conflicts where one raw reference could point to multiple targets
- preserve resolver reasons and confidence
- keep rejected or deferred candidates from reappearing as fresh unknowns

### Data Contract: `reference_resolution`

```json
{
  "resolution_id": "uuid",
  "reference_id": "uuid",
  "target_type": "author",
  "target_id": "cicero",
  "target_display": "Cicero",
  "target_status": "non_acquired",
  "external_ids": {
    "wikidata": "Q1541"
  },
  "resolver_method": "catalog_alias_external_id",
  "confidence": 0.91,
  "reason": "Name match plus external identifier.",
  "review_status": "pending_review"
}
```

### Acceptance

- acquired authors resolve to existing slugs
- queued/rejected authors are recognized from ledgers
- unknown targets remain reviewable
- target identity changes invalidate dependent candidate edges and leads

## Agent 4: Cross-Reference Agent

### Mission

Build evidence-backed relationships from resolved references.

### Inputs

- reviewed or confidence-gated references
- reference resolutions
- source and target passage metadata
- semantic neighbor rows when available
- approved source-card metadata when available

### Relationship Types

- direct citation
- quoted text
- author mention
- work mention
- scripture reference
- allusion
- shared theme
- contrast
- reception
- influence
- doctrinal parallel

### Data Contract: `cross_reference_edge`

```json
{
  "edge_id": "uuid",
  "source_passage_id": "augustine/confessions/8/12",
  "target_type": "author",
  "target_id": "cicero",
  "relationship_type": "author_mention",
  "supporting_reference_id": "uuid",
  "evidence_source_span": "Cicero",
  "evidence_target_span": null,
  "confidence": 0.91,
  "review_status": "pending_review",
  "run_id": "uuid",
  "created_at": "2026-07-05T00:00:00Z"
}
```

### Acceptance

- every edge has a supporting reference
- passage-to-passage edges include anchors on both sides when target text exists
- rejecting a supporting reference invalidates dependent edges
- public APIs expose only reviewed or confidence-gated edges

## Agent 5: Author Discovery Agent

### Mission

Identify non-acquired authors and works that deserve acquisition review because
they are connected to the acquired corpus.

### Inputs

- references with `target_status=non_acquired` or `unknown`
- cross-reference edges
- acquisition ledger statuses
- approved source metadata when available
- prior rejection/defer history

### Candidate Classes

- inbound reception: outside authors reference acquired authors
- outbound influence: acquired authors reference non-acquired authors
- peer cluster: multiple acquired authors reference the same non-acquired author
- bridge candidate: one non-acquired author connects separate traditions
- work-first candidate: a work is important before its author is fully modeled

### Data Contract: `author_discovery_lead`

```json
{
  "lead_id": "uuid",
  "candidate_author_name": "Cicero",
  "candidate_work_title": "De Officiis",
  "candidate_status": "non_acquired",
  "relationship_summary": "Referenced by an acquired Augustine passage.",
  "primary_acquired_author_slug": "augustine",
  "primary_acquired_work_id": "confessions",
  "supporting_reference_ids": ["uuid"],
  "supporting_edge_ids": ["uuid"],
  "priority_score": 0.82,
  "priority_reason": "Bridge candidate connected to acquired Latin tradition.",
  "rights_status": "unknown",
  "source_availability_status": "metadata_needed",
  "review_status": "pending_review",
  "next_action": "review_for_author_acquisition"
}
```

### Acceptance

- every lead cites supporting references
- duplicate name/work variants collapse safely
- rejected/deferred leads do not churn unless new evidence appears
- lead creation never implies source text acquisition

## Agent 6: Acquisition Handoff Agent

### Mission

Turn approved author discovery leads into safe acquisition queue proposals.

### Inputs

- approved author discovery leads
- `AugustineService/metadata/author_acquisition.json`
- `fortress-phronesis/docs/author_acquisition.json`
- `docs/author-acquisition-process.md`

### Responsibilities

- generate ledger diffs in dry-run mode
- check both ledgers for drift
- prevent duplicate author/work entries
- demote stale `next-up` entries when needed
- generate status strings that preserve production publication and public
  verification gates
- run JSON validation before any proposed write
- keep reviewer approval attached to the proposal

### Output: `acquisition_handoff_proposal`

```json
{
  "proposal_id": "uuid",
  "lead_id": "uuid",
  "candidate_author_name": "Cicero",
  "recommended_status": "next-up queued; pending text acquisition",
  "ledger_targets": [
    "AugustineService/metadata/author_acquisition.json",
    "fortress-phronesis/docs/author_acquisition.json"
  ],
  "dry_run_diff": "...",
  "validation_status": "passed",
  "requires_human_approval": true
}
```

### Acceptance

- a lead can enter the acquisition queue only after approval
- both ledgers remain synchronized
- invalid JSON cannot be produced silently
- no queued status claims runtime wiring, production publication, or public
  verification before those gates pass

## Agent 7: Operator Review Agent

### Mission

Make the reference-intelligence workflow reviewable in `fortress.local`.

### Review Inboxes

- extraction runs
- unresolved references
- low-confidence references
- duplicate/merge candidates
- candidate cross-reference edges
- non-acquired author leads
- acquisition handoff proposals
- rejected/deferred items with new evidence

### Required Actions

- approve
- reject
- defer
- merge target
- mark needs source review
- mark needs rights review
- approve for acquisition handoff

### Audit Contract

Every action records:

- actor
- timestamp
- old state
- new state
- reason or note
- source object ID
- run ID where applicable

### Acceptance

- the owner can answer "why is this reference/author recommended?"
- all state changes are auditable
- operator UI cannot directly publish authors
- rejected/deferred records stop reappearing without new evidence

## Agent 8: Reader Reference Adapter

### Mission

Expose reviewed reference intelligence to PericopeAI users without exposing
internal graph or acquisition workflow state.

### Inputs

- reviewed references
- reviewed cross-reference edges
- approved source-card metadata when available
- public visibility rules

### Reader-Facing Outputs

- related passages
- related authors
- related works
- "referenced by" reverse lookup rows
- citation provenance detail
- evidence snippets

### Hidden From Reader UI

- raw graph topology
- extraction run internals
- low-confidence pending references
- unreviewed author leads
- operator notes
- rights-risk records

### Acceptance

- chat still works if reference intelligence is unavailable
- reader UI shows evidence and provenance, not raw internal infrastructure
- unreviewed acquisition leads never appear in public product surfaces

## Persistence Plan

Phase 1 should use MySQL or MySQL-backed relational tables. A graph database can
be evaluated later as a derived read model, not a canonical store.

Recommended first tables or equivalent records:

- `reference_job_runs`
- `resolved_references`
- `reference_resolutions`
- `cross_reference_edges`
- `author_discovery_leads`
- `operator_review_actions`
- `acquisition_handoff_proposals`

Rules:

- MySQL remains canonical until an explicit migration decision.
- A graph DB is not required for the first release.
- Graph-shaped queries may be backed by relational views first.
- Any future graph service must be added only through Fortress Phronesis and
  workspace deployment locks.

## API and Job Boundaries

Initial commands should be local/operator-only:

```bash
reference-intel scan --scope author:augustine
reference-intel scan --scope work:confessions
reference-intel resolve --run-id <run_id>
reference-intel build-edges --run-id <run_id>
reference-intel build-author-leads --run-id <run_id>
reference-intel handoff --lead-id <lead_id> --dry-run
```

Candidate operator APIs:

- `GET /control/api/pericope/reference-intel/runs`
- `GET /control/api/pericope/reference-intel/references/pending`
- `POST /control/api/pericope/reference-intel/references/{reference_id}/review`
- `GET /control/api/pericope/reference-intel/edges/pending`
- `POST /control/api/pericope/reference-intel/edges/{edge_id}/review`
- `GET /control/api/pericope/reference-intel/author-leads`
- `POST /control/api/pericope/reference-intel/author-leads/{lead_id}/review`
- `POST /control/api/pericope/reference-intel/handoff/{lead_id}/dry-run`

If any endpoint becomes public or user-facing, it must enforce authentication,
authorization, ownership, redaction, rate limits, and scope limits.

## Implementation Phases

### Phase 0: Contracts and Fixtures

Deliverables:

- schema draft for all records
- fixture passages for direct citation, scripture reference, author mention,
  work mention, allusion, ambiguity, and false positive
- review-status vocabulary
- target-status vocabulary
- first CLI stub with dry-run output

Exit criteria:

- fixtures prove source evidence is preserved
- fixtures prove ambiguous references remain reviewable
- no acquisition ledger files are touched

### Phase 1: Citations Agent and Resolver

Deliverables:

- deterministic extraction for scripture, author names, work titles, and quotes
- resolver against internal catalogs and acquisition ledgers
- persisted references and resolutions
- run summary report

Exit criteria:

- known acquired corpus passages produce expected references
- queued and rejected authors are recognized
- unresolved targets are visible for review

### Phase 2: Cross-Reference Edge Builder

Deliverables:

- edge builder from reviewed/confidence-gated references
- reverse lookup views by author, work, passage, and scripture
- edge invalidation when references change
- internal API or export shape for reviewed edges

Exit criteria:

- every edge points to supporting evidence
- reverse lookup works for at least one acquired author and one scripture target
- rejected references remove dependent candidate edges from reviewed output

### Phase 3: Author Discovery

Deliverables:

- lead builder for non-acquired and unknown targets
- dedupe/merge logic
- priority scoring
- suppression rules for rejected/deferred leads
- lead explanation bundle

Exit criteria:

- each lead is explainable by references and edges
- duplicate candidates collapse safely
- no lead mutates acquisition ledgers

### Phase 4: Operator Review in `fortress.local`

Deliverables:

- review inbox views
- approve/reject/defer/merge actions
- audit trail
- run history and failure detail
- high-priority author lead view

Exit criteria:

- owner can review and act on references, edges, and leads
- audit records exist for all decisions
- operator UI cannot bypass acquisition gates

### Phase 5: Acquisition Handoff

Deliverables:

- handoff proposal generator
- ledger dry-run diff
- JSON validation
- synchronized update check for both acquisition ledgers
- status-string guardrails aligned to `docs/author-acquisition-process.md`

Exit criteria:

- approved lead can become a queue proposal
- both ledgers remain synchronized
- production completion is not claimed before public verification

### Phase 6: Reader-Facing Consumption

Deliverables:

- reviewed references response shape
- related passages/authors/works payload
- provenance detail payload
- frontend display rules
- fallback behavior when reference intelligence is unavailable

Exit criteria:

- PericopeAI can show reviewed related references
- pending/rejected records remain hidden
- chat behavior remains intact if the reference layer fails

## Testing Plan

Required tests:

- extraction fixture tests
- source-offset/evidence-span tests
- resolver tests for acquired, queued, rejected, non-acquired, and unknown
  targets
- false-positive tests for ambiguous names and work titles
- edge-builder tests requiring supporting references
- edge invalidation tests
- author-lead dedupe tests
- priority scoring tests
- handoff dry-run tests
- JSON validation tests for both acquisition ledgers
- operator API authorization tests
- reader-facing visibility tests
- failure/fallback tests proving chat still works without reference intelligence

## Observability

Track:

- job run duration
- passages scanned
- references extracted
- unresolved reference count
- low-confidence reference count
- resolver conflict count
- cross-reference edges created
- edges rejected or invalidated
- author leads created
- author leads approved, rejected, deferred, or marked rights review
- handoff proposals created
- ledger validation failures
- external resolver failures when external IDs are used
- backlog count by review status

Logs must not include API keys, bearer tokens, private prompts, cookies,
authorization headers, or unrelated private notes.

## Definition of Done

The first complete release is done when:

- `fortress.lan` can run a bounded reference scan for one acquired author
- references and resolutions persist with evidence
- reviewed cross-reference edges can be queried
- non-acquired author leads are generated with supporting evidence
- `fortress.local` can approve/reject/defer leads
- an approved lead can produce an acquisition handoff dry-run
- both acquisition ledgers validate after a proposed change
- PericopeAI can show reviewed related references without exposing unreviewed
  leads
- deployment docs still confirm no new public route, host port, service, or env
  var was introduced

## Open Questions

- Which local control-plane project owns the first `fortress.local` review UI:
  `local_tools`, `fortress-lan`, or a Pericope-specific panel?
- Should first persistence live in the PericopeAI MySQL database or a separate
  operator database on Fortress LAN?
- What confidence threshold is high enough for reader-facing display without
  manual review?
- Should author discovery leads be ranked globally, per tradition, or per
  acquired author cluster?
- Which external identifiers are mandatory before a non-acquired author can be
  queued?
- Should rejected author leads expire after a time window or stay suppressed
  until new evidence appears?
