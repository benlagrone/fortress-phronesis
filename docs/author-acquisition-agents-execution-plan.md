# Author Acquisition Agents Execution Plan

**Status:** active development
**Owner surface:** Fortress Phronesis docs and PericopeAI corpus operations
**Runtime target:** Fortress LAN background jobs with local operator review
**Current deployed source of truth:** existing author-acquisition ledgers plus the corpus/runtime stack
**Architecture diagram:** [author-acquisition-agents-architecture.mmd](author-acquisition-agents-architecture.mmd)
**Deployment note:** This plan does not add a deployed service, public route, host port, environment variable, or deployment path by itself.

## Purpose

PericopeAI's author-acquisition tracker has enough pending, partially wired, and
historical-status work that a manual queue is no longer the right operating
model. The agent system should move acquisition forward while preserving the
hard gates in `author-acquisition-process.md`.

The system must answer four operational questions:

1. Which tracked authors are actually incomplete?
2. Which acquired authors are missing important publications?
3. Which new authors or works should be proposed for the queue?
4. Which approved source texts can be safely acquired, indexed, published, and
   publicly verified?

The system is an operator workflow, not an autonomous publishing pipeline.

## Current Tracker Snapshot

The Phase 0 CLI recalculates at run time whether the two ledgers are
synchronized:

- `fortress-phronesis/docs/author_acquisition.json`
- `AugustineService/metadata/author_acquisition.json`

Current ledger counts:

- 97 total entries
- 75 `pending`
- 12 `texts downloaded; index built; runtime wired`
- 5 `texts present; index volume wired`
- 5 `texts downloaded; prod corpus synced; index built; runtime wired; public verification passed`

This snapshot is planning context only. The agents must recalculate these counts
from the ledgers at run time.

## Relationship To Existing Plans

`reference-intelligence-agents-implementation-plan.md` owns extraction,
reference resolution, cross-references, non-acquired author discovery leads,
acquisition handoff proposals, operator review, and reader-facing reference
outputs.

This plan owns the author-acquisition execution layer:

- tracker stewardship
- publication-gap audits for acquired authors
- new candidate queue proposals
- source discovery and source-card preparation for acquisition
- local corpus acquisition
- local runtime wiring and indexing
- production publication handoff
- public verification evidence

Reference intelligence can create acquisition leads, but it must not download
source text, mutate author ledgers, claim production completion, or publish
authors. This plan begins where approved acquisition intent needs to become
safe operational work.

## Operating Model

Use the same two-plane control pattern as the reference-intelligence plan:

- `fortress.lan` runs bounded background jobs for audits, source discovery,
  downloads, normalization, indexing, local checks, and public verification.
- `fortress.lan` presents the canonical review queues, evidence packets,
  approvals, rejects, deferrals, run status, and failure recovery control
  surface, with `fortress.local` available as the workstation mirror route.
- `pericopeai.local` is used for local runtime verification.
- `https://pericopeai.com` is used only for public verification after an
  approved production publication path.

No agent may silently acquire, publish, or mark an author complete. Completion
requires the gates in `author-acquisition-process.md`.

## Architecture Diagram

Canonical Mermaid source:

`docs/author-acquisition-agents-architecture.mmd`

The `.mmd` file is the diagram source of truth. Keep this section as the
reader-facing architecture contract and update the Mermaid file when the
execution flow changes.

The diagram separates the system into seven execution tracks:

1. `Tracker Control`: validates the two ledgers, status vocabulary, duplicate
   names, and write safety before any proposed ledger update.
2. `Discovery And Source Review`: turns backlog, coverage gaps, and reference
   intelligence leads into candidate packets, publication-gap packets, source
   cards, and download plans.
3. `Local Corpus Build`: downloads or curates only approved sources, normalizes
   texts, prepares metadata diffs, and builds author-scoped indexes.
4. `Local Runtime Verification`: verifies catalog, profile, portrait, compose
   wiring, and grounded retrieval through `pericopeai.local`.
5. `Publication Handoff And Public Verification`: prepares the governed
   production sync checklist, stops for explicit approval, then captures public
   evidence before any complete status is allowed.
6. `Operator Plane`: keeps `fortress.lan` as the canonical review surface for
   packet approval, rejection, deferral, run history, and audit trail, with
   `fortress.local` as the workstation mirror.
7. `Deployment Boundary`: preserves the workspace deployment lock and requires
   deployed-architecture/runbook updates only when a runtime surface changes.

The critical gates are:

- `Ledger sync guard`: both ledgers must parse and match before writes are
  proposed.
- `Ledger write approved`: ledger mutations require a dry-run diff and operator
  approval.
- `Source card approved`: full-text ingestion requires reviewed provenance and
  rights status.
- `Local verification passed`: publication handoff is not proposed until local
  catalog/profile/retrieval checks pass.
- `Explicit approval for production mutation`: production corpus sync, indexing,
  or restart cannot run from background automation alone.
- `Public verification passed`: complete status is blocked until public
  catalog/profile/media/runtime evidence is attached.

## Agent Roles

These are roles inside one author-acquisition system. They do not require
separate repositories or independent deployment surfaces.

| Agent | Owns | Main output |
| --- | --- | --- |
| Tracker Steward | ledger inventory, status validation, drift detection | tracker audit report |
| Coverage Auditor | missed-publication checks for acquired authors | publication gap packets |
| Candidate Scout | new author/work proposals | candidate packets |
| Source Steward | source discovery, provenance, edition, rights review proposals | source cards |
| Acquisition Operator | approved local acquisition, normalization, metadata, indexing | local acquisition run |
| Runtime Verifier | local catalog/profile/retrieval checks | verification packet |
| Publication Handoff | production corpus sync and activation proposal | gated release packet |
| Public Verifier | public catalog/profile/media/runtime verification | public evidence packet |
| Operator Review | review queues, approvals, audit trail | approved/rejected/deferred actions |

## Capability Inventory

### 1) Ledger And Tracker Capabilities

Required tools:

- read both acquisition ledgers
- compare ledgers byte-for-byte and semantically
- summarize status counts
- detect duplicate names and probable duplicate aliases
- validate JSON before and after proposed edits
- generate dry-run diffs for ledger changes
- block writes unless both target ledgers are synchronized or a reconciliation
  proposal has been approved

Inputs:

- `fortress-phronesis/docs/author_acquisition.json`
- `AugustineService/metadata/author_acquisition.json`
- `fortress-phronesis/docs/author-acquisition-process.md`

Outputs:

- `tracker_audit_report`
- `ledger_reconciliation_proposal`
- `ledger_update_dry_run`

Acceptance:

- agent can state which entries are pending, partial, legacy-complete, or
  publicly verified
- agent cannot write invalid JSON
- agent cannot claim completion with legacy statuses that omit production corpus
  sync and public verification

### 2) Bibliographic And Coverage Capabilities

Required tools:

- extract local works from corpus text directories, author metadata, and book
  metadata
- normalize titles, subtitles, alternate spellings, translations, and fragments
- compare local works against known bibliographic inventories
- query a bounded public-domain catalog for already acquired authors
- classify missing works by confidence and actionability
- suppress duplicates already present under alternate titles

Candidate external metadata/source surfaces:

- Project Gutenberg or Gutendex
- Internet Archive metadata
- Open Library
- Wikidata and Wikimedia Commons
- Crossref and OpenAlex for bibliographic metadata
- domain-specific public-domain libraries such as Perseus, CCEL, and similar
  source collections when appropriate

Phase 0 CLI note:

- `audit-coverage` should resolve a likely canonical author record first and
  then inspect bounded works metadata from Open Library.
- Gutendex remains a supplemental source for public-domain full-text candidates
  when catalog-level evidence needs a likely ingestable text surface.

Outputs:

- `publication_gap_packet`
- `work_alias_map`
- `coverage_maturity_report`

Gap classifications:

- `missing_usable_public_domain_text`
- `bibliographic_record_only`
- `already_present_under_alternate_title`
- `fragmentary_or_dubious_attribution`
- `rights_sensitive`
- `low_priority`

Acceptance:

- every proposed gap includes evidence of why it is missing
- every ingestable gap includes source and provenance candidates
- no modern or rights-sensitive work is routed to ingestion without review
- already acquired or publicly verified authors can still emit new gap packets
  when the audit finds likely missing public-domain works

### 3) Candidate Scout Capabilities

Required tools:

- read tracker backlog and existing author taxonomy
- consume approved reference-intelligence acquisition leads
- identify tradition/domain gaps in the current catalog
- score candidate fit, source availability, rights risk, expected product value,
  and acquisition difficulty
- produce candidate packets without editing the ledger

Inputs:

- acquisition ledgers
- author taxonomy and biographies
- reference-intelligence author leads, when available
- user-specified priorities

Outputs:

- `candidate_author_packet`
- `candidate_work_packet`

Acceptance:

- candidates are proposed with rationale and evidence
- rejected/deferred candidates do not churn back into the queue without new
  evidence
- no candidate becomes a ledger entry without explicit approval

### 4) Source Steward Capabilities

Required tools:

- search approved metadata and text sources
- capture source URL, edition, translator/editor when relevant, license or
  public-domain rationale, and retrieval date
- check whether source quality is sufficient for a PericopeAI persona
- prepare source cards for operator review
- produce a download plan only after the source card is approved

Outputs:

- `source_candidate`
- `source_card`
- `download_plan`

Acceptance:

- every source card has provenance and a rights/review status
- the agent distinguishes metadata discovery from full-text ingestion
- the agent can mark `needs_rights_review` without blocking unrelated safe work

### 5) Local Acquisition Capabilities

Required tools:

- download or curate approved source texts
- place texts under `AugustineCorpus/texts/<author_slug>_texts/`
- normalize text files
- generate or update book metadata
- update author catalog metadata as a dry run first
- build or refresh author indexes locally

Existing command family:

```bash
python AugustineCorpus/scripts/download_author_works.py --author "<name>" --slug <slug>
python AugustineCorpus/scripts/normalize_downloaded_texts.py ...
python AugustineCorpus/scripts/generate_book_metadata.py ...
python AugustineCorpus/preprocess_and_index.py --author <slug> --texts-root AugustineCorpus/texts
python AugustineCorpus/scripts/index_author.py --author <slug> --texts-root AugustineCorpus/texts
```

Outputs:

- `local_acquisition_run`
- normalized text files
- book metadata diff
- index build report

Acceptance:

- text files exist and are non-empty
- metadata validates
- index artifacts exist for the author
- local runtime checks pass before any production handoff is proposed

### 6) Runtime Verification Capabilities

Required tools:

- query local corpus catalog
- query local author profile behavior
- run author-scoped retrieval/context checks
- verify portrait/media metadata where present
- verify runtime wiring in compose before status changes

Minimum local checks:

- author appears in local author catalog
- author profile resolves
- text directory is mounted read-only where required
- index volume is wired
- grounded retrieval returns citations for a representative question

Outputs:

- `local_runtime_verification_packet`

Acceptance:

- failures are actionable and tied to exact files/routes
- `runtime wired` is never treated as production completion

### 7) Publication Handoff Capabilities

Required tools:

- prepare a production publication checklist
- verify corpus payload is ready for upload
- propose use of the governed corpus sync/upload path
- propose author-scoped production indexing
- propose required service restarts
- stop for explicit approval before any production mutation

Relevant governed references:

- `author-acquisition-process.md`
- `pericopeai-deployment.md`
- `release-runbook-prod-v1.1.1.md`
- `../scripts/upload-corpus.sh`

Outputs:

- `publication_handoff_packet`
- `production_activation_checklist`

Acceptance:

- production handoff does not create a competing deployment path
- no production sync or restart occurs without explicit approval
- proposed status strings preserve pending-public-verification state until
  public checks pass

### 8) Public Verification Capabilities

Required tools:

- call public author catalog
- call public author profile
- verify public portrait/media path
- run public grounded retrieval/runtime check when applicable
- capture evidence and failure details

Minimum public checks:

- public `/api/v1/authors` presence when the author is meant to be public
- public `/api/v1/authors/{slug}/profile`
- public portrait/media path if one exists
- grounded retrieval/runtime behavior for the author when applicable

Outputs:

- `public_verification_packet`

Acceptance:

- public verification evidence is attached to any complete status
- failed public verification leaves the author in a pending state
- verification logs do not include secrets or private prompts

### 9) Operator Communication Capabilities

Required tools:

- `fortress.local` review inbox
- approval actions for add, defer, reject, merge, acquire, index, publish, and
  verify
- audit trail with actor, timestamp, reason, and old/new state
- run history and retry/cancel controls
- optional Moltbot notification only as a communication channel

Review packet types:

- tracker audit
- coverage gap
- candidate author
- source card
- local acquisition run
- local runtime verification
- publication handoff
- public verification

Acceptance:

- owner can answer "why is this proposed?"
- owner can approve safe next actions without reading raw logs
- operator UI cannot bypass acquisition gates

## Full Delivery Execution Plan

The delivery plan is split into six execution tracks. Tracks can run in
parallel, but each track must emit reviewable artifacts before a later track can
perform state-changing work.

### Execution Tracks

| Track | Purpose | First owner | First artifact |
| --- | --- | --- | --- |
| Tracker Control | keep the two ledgers valid and synchronized | Tracker Steward | `tracker_audit_report` |
| Coverage Audit | find missing works for acquired or partially acquired authors | Coverage Auditor | `publication_gap_packet` |
| Candidate Pipeline | propose new authors/works and prioritize the backlog | Candidate Scout | `candidate_author_packet` |
| Source Pipeline | find usable source text and rights/provenance evidence | Source Steward | `source_card` |
| Local Build Pipeline | acquire, normalize, metadata-build, index, and local-verify | Acquisition Operator | `local_acquisition_run` |
| Release Pipeline | prepare prod publication, activate, and public-verify | Publication Handoff/Public Verifier | `public_verification_packet` |

### Backlog Segmentation

Every daily run should bucket the tracker into operational segments:

- `pending`: candidate/source-card work is needed before acquisition.
- `texts_present_index_volume_wired`: local inventory must be reconciled against
  explicit index, runtime, production, and public-verification evidence.
- `legacy_runtime_wired`: local runtime may work, but production corpus sync and
  public verification are not proven.
- `pending_prod_corpus_sync`: local acquisition is complete enough to prepare a
  governed publication handoff.
- `pending_public_verification`: production activation may be complete, but the
  public evidence packet is missing or failed.
- `public_verification_passed`: complete only if the evidence packet remains
  available and current.

Tracker stewardship must also distinguish `key works` metadata from the full
works inventory. The ledger inventory is expected to enumerate all acquired
corpus titles for the author, and coverage audits should warn when the ledger
underreports what `AugustineCorpus` already mounts.
Coverage audits must also search for likely missing public-domain works beyond
the current corpus and emit `publication_gap_packet` items for operator review
instead of treating previously shipped authors as permanently exhaustive.

The first priority is not the largest group. The priority order is:

1. Ledger safety and drift prevention.
2. Legacy/runtime-wired cleanup, because these are closest to completion.
3. Texts-present/index-volume reconciliation.
4. Coverage audits for public or heavily used authors.
5. Pending candidate/source-card pipeline.

### Operating Cadence

Daily automated dry-run:

```bash
python3 scripts/author-acq.py validate-ledgers
python3 scripts/author-acq.py audit-tracker --dry-run --format json
python3 scripts/author-acq.py audit-coverage --format json
python3 scripts/author-acq.py status-report
```

Daily agent work targets after Phase 1 exists:

- run tracker audit once
- run coverage audit for 5-10 authors or one full status segment
- prepare 2-5 source/candidate packets
- move at most 1 approved author/work through local acquisition until the flow is
  stable
- produce a daily review report for `fortress.local`

Weekly production rhythm after Phase 6 exists:

- Monday: backlog and coverage audit review
- Tuesday-Wednesday: approved local acquisition and indexing
- Thursday: local verification and publication handoff preparation
- Friday: production publication only if explicitly approved and verification
  windows are clear
- Weekend: no unattended production publication; dry-run audits only

Initial throughput targets:

- candidate/source-card proposals: 10-20 per week
- local acquisitions: 3-5 bounded works per week
- fully public verified authors: 1-3 per week once the release path is stable
- large authors or disputed/rights-sensitive sources: no throughput target until
  source review is complete

### Review State Machine

All review packets use the same state vocabulary:

```text
draft
pending_review
approved
rejected
deferred
needs_source_review
needs_rights_review
needs_local_repair
needs_public_repair
completed
superseded
```

State-change rules:

- `draft` packets may be overwritten by the same run.
- `pending_review` packets are immutable except for review metadata.
- `approved` packets may trigger the next track but only within their approved
  action scope.
- `rejected` and `deferred` packets must not reappear as new work unless new
  evidence is attached.
- `completed` requires the relevant evidence packet, not just a status string.
- `superseded` must point to the replacement packet ID.

### Approval Gates

The following gates are mandatory:

| Gate | Approval required before | Minimum evidence |
| --- | --- | --- |
| Ledger write | any change to either acquisition ledger | dry-run diff, JSON validation, sync check |
| Source ingestion | any full-text download/curation | approved source card |
| Local index build | index mutation or rebuild | local acquisition packet and text inventory |
| Production corpus sync | upload/sync to production host | publication handoff packet |
| Service restart | production restart or activation | approved production checklist |
| Complete status | public verification passed | public evidence packet |

### Monitoring Artifacts

Before `fortress.local` UI exists, the CLI should write local artifacts under an
ignored runtime directory:

```text
tmp/author-acq/
  runs/<run_id>/tracker-audit.json
  runs/<run_id>/status-report.json
  runs/<run_id>/coverage-audit.json
  review-packets/<packet_id>.json
  daily/<YYYY-MM-DD>.md
```

These files are local operator artifacts. Do not commit them unless a specific
fixture is intentionally added under `tests/fixtures/`.

Current operator-surface contract:

- the canonical review UI is `http://fortress.lan/author-acquisition`
- `http://fortress.local/author-acquisition` remains the workstation mirror
  route
- the Fortress LAN page is read-only and calls
  `fortress-phronesis/scripts/author_acq.py` for tracker and coverage JSON
- Pericope feature/UI repos do not own this operator dashboard

Minimum daily report:

```text
# Author Acquisition Daily Report - YYYY-MM-DD

Tracker:
- total entries
- counts by status
- ledger sync status
- write guard status

Advanced:
- source cards created
- coverage gaps created
- local acquisitions completed
- local verifications passed
- public verifications passed

Blocked:
- rights review
- source ambiguity
- local indexing failure
- public verification failure

Next approvals needed:
- packet id, author/work, requested action
```

### Progress Metrics

Track these metrics per day and per week:

- `ledger_total_entries`
- `ledger_sync_blocked`
- `pending_count`
- `legacy_runtime_wired_count`
- `texts_present_index_volume_wired_count`
- `source_cards_created`
- `source_cards_approved`
- `coverage_gap_packets_created`
- `candidate_packets_created`
- `local_acquisition_runs_started`
- `local_acquisition_runs_completed`
- `local_verification_passed`
- `publication_handoffs_created`
- `public_verification_passed`
- `public_verification_failed`
- `review_packets_pending`
- `review_packets_blocked_rights`
- `review_packets_blocked_local_repair`

### Monitoring Surfaces

Phase 0-1:

- CLI output
- JSON artifacts under `tmp/author-acq`
- Markdown daily report

Phase 2-4:

- local review packet index
- run history JSON
- terminal command summaries

Phase 5:

- `fortress.local` review inbox
- kanban columns by review state
- packet detail page with evidence, diff, and approval controls

Phase 6:

- `fortress.local` release dashboard
- public verification evidence table
- production handoff queue
- failed verification repair queue

### 30-Day Build Sequence

This schedule assumes focused development and no production topology changes.

#### Days 1-3: Tracker Control

Status: started.

Deliver:

- `author-acq validate-ledgers`
- `author-acq status-report`
- `author-acq audit-tracker --dry-run`
- tests for sync, drift, duplicate names, and unknown statuses
- daily report skeleton

Done when:

- every run can answer whether the ledgers are safe to write
- status counts are generated from the live files
- output is usable as a `tracker_audit_report`

#### Days 4-7: Coverage Audit

Deliver:

- local work extractor from text directories and known metadata
- slug/name lookup from the ledger
- `audit-coverage --author <slug>`
- `audit-coverage --status <status>`
- `publication_gap_packet` schema and fixture tests

Done when:

- `hermes_trismegistus` and all `legacy_runtime_wired` authors can be audited
- local works are listed with source paths
- potential missing works are emitted as review packets, not downloads

#### Days 8-11: Candidate And Source Packet Foundation

Deliver:

- candidate packet schema
- source card schema
- source provider adapter interface
- metadata-only source lookup for one safe provider class
- packet dedupe by author/work/source URL

Done when:

- pending entries can get source-card work queued
- candidate packets can be generated without ledger writes
- packet review status is persisted locally

#### Days 12-16: Source Discovery

Deliver:

- source search for priority pending authors and missing works
- rights/provenance fields
- `find-sources --author <name> --work <title> --dry-run`
- `prepare-source-card --source-url <url> --dry-run`

Done when:

- 10 source cards can be prepared for review
- rights-sensitive records are separated from safe public-domain candidates
- no full-text ingestion happens without an approved source card

#### Days 17-21: Local Acquisition Runner

Deliver:

- guarded `acquire-local --dry-run`
- approved `acquire-local --execute`
- command construction around existing download/normalize/metadata/index tools
- file inventory and rollback notes for local changes
- local verification packet stub

Done when:

- one bounded author/work can be acquired locally after approval
- metadata and text inventory validate
- index build command is reproducible and logged

#### Days 22-25: Local And Public Verification

Deliver:

- `verify-local --author <slug>`
- `prepare-publication --author <slug> --dry-run`
- `verify-public --author <slug>`
- status finalizer dry-run with required evidence packet

Done when:

- local catalog/profile/retrieval checks produce machine-readable evidence
- public catalog/profile/media checks produce machine-readable evidence
- no complete status can be produced without a passing public packet

#### Days 26-30: Fortress Review Surface

Deliver:

- review packet index endpoint or static JSON export
- `fortress.local` queue design with columns by review status
- approve/reject/defer action contract
- audit event schema
- daily report rendered from packet/run data

Done when:

- the owner can review packets without terminal access
- approval actions are auditable
- the UI cannot bypass publication gates

### First Seven-Day Execution Checklist

1. Keep Phase 0 tests passing.
2. Add `tmp/author-acq/` to ignored runtime artifacts if it does not already
   resolve as ignored.
3. Add `author_acq` run ID generation and JSON artifact output.
4. Implement local work extraction.
5. Implement `audit-coverage --author hermes_trismegistus --dry-run`.
6. Add fixture tests for local works and publication gap packets.
7. Run coverage audit for all `legacy_runtime_wired` authors and produce the
   first daily Markdown report.

## Data Contracts

### `author_acquisition_job_run`

```json
{
  "run_id": "uuid",
  "job_type": "coverage_audit",
  "scope_type": "author",
  "scope_value": "augustine",
  "status": "running",
  "started_at": "2026-07-06T00:00:00Z",
  "finished_at": null,
  "counts": {
    "items_seen": 0,
    "packets_created": 0,
    "errors": 0
  }
}
```

### `candidate_author_packet`

```json
{
  "candidate_id": "uuid",
  "name": "Thomas Aquinas",
  "proposed_slug": "thomas_aquinas",
  "persona_mode": "Authority",
  "rationale": "Major scholastic synthesis connected to Aristotle and Augustine.",
  "key_works": ["Summa Theologiae", "Summa Contra Gentiles"],
  "source_availability_status": "metadata_found",
  "rights_status": "needs_review",
  "priority_score": 0.91,
  "review_status": "pending_review"
}
```

### `publication_gap_packet`

```json
{
  "gap_id": "uuid",
  "author_slug": "augustine",
  "work_title": "On Christian Doctrine",
  "local_status": "not_found",
  "source_candidates": ["source-card-id"],
  "classification": "missing_usable_public_domain_text",
  "confidence": 0.86,
  "review_status": "pending_review"
}
```

### `source_card`

```json
{
  "source_id": "uuid",
  "author_name": "Adam Smith",
  "work_title": "The Theory of Moral Sentiments",
  "source_url": "https://example.invalid/source",
  "source_type": "full_text",
  "edition_note": "edition metadata here",
  "rights_status": "needs_review",
  "provenance_note": "discovery and access evidence here",
  "review_status": "pending_review"
}
```

### `acquisition_action_packet`

```json
{
  "action_id": "uuid",
  "author_slug": "adam_smith",
  "action_type": "download_and_normalize",
  "inputs": ["source-card-id"],
  "dry_run": true,
  "requires_human_approval": true,
  "expected_file_changes": [
    "AugustineCorpus/texts/adam_smith_texts/..."
  ]
}
```

## Execution Phases

### Phase 0: Contracts And Dry-Run CLI

Deliverables:

- schema drafts for all packet types
- tracker audit command
- ledger sync validator
- status vocabulary validator
- fixture output for at least one public-verified author, one legacy
  runtime-wired author, and one pending author

Candidate commands:

```bash
python3 scripts/author-acq.py audit-tracker --dry-run
python3 scripts/author-acq.py validate-ledgers
python3 scripts/author-acq.py status-report
```

Exit criteria:

- both ledgers are read and validated
- current counts are reproduced from source files
- no files are changed
- invalid or legacy statuses are reported with recommended next actions

### Phase 1: Coverage Auditor

Deliverables:

- local work extractor
- title normalization and alias handling
- missed-publication detector
- coverage maturity report per author

Candidate commands:

```bash
author-acq audit-coverage --author augustine --dry-run
author-acq audit-coverage --status "texts downloaded; index built; runtime wired" --dry-run
```

Exit criteria:

- acquired and partially acquired authors get coverage reports
- gaps are classified by actionability and rights risk
- no downloads occur

### Phase 2: Candidate Scout

Deliverables:

- candidate packet generator
- integration point for approved reference-intelligence leads
- duplicate and rejection suppression
- priority scoring

Candidate commands:

```bash
author-acq propose-candidates --from-ledger-gaps --dry-run
author-acq propose-candidates --from-reference-leads --dry-run
```

Exit criteria:

- new authors are proposed with evidence and rationale
- no ledger edits occur without approval

### Phase 3: Source Steward

Deliverables:

- source search adapters
- source cards
- rights/provenance review status
- download plans for approved source cards

Candidate commands:

```bash
author-acq find-sources --author adam_smith --work "The Theory of Moral Sentiments" --dry-run
author-acq prepare-source-card --source-url <url> --dry-run
```

Exit criteria:

- every ingest proposal points to a reviewed source card
- metadata-only discovery is separated from full-text ingestion

### Phase 4: Local Acquisition Operator

Deliverables:

- approved download/curation runner
- normalization runner
- metadata generation runner
- index build runner
- local verification packet

Candidate commands:

```bash
author-acq acquire-local --author <slug> --source-card <id> --dry-run
author-acq acquire-local --author <slug> --source-card <id> --execute
author-acq verify-local --author <slug>
```

Exit criteria:

- local files, metadata, and indexes validate
- local profile and retrieval checks pass
- ledger status can advance only to the correct local or pending-prod state

### Phase 5: Fortress Operator Review

Deliverables:

- `fortress.local` review queues
- run history
- approve/reject/defer/merge actions
- audit records
- dry-run diff display

Candidate local control endpoints:

- `GET /control/api/pericope/author-acq/runs`
- `GET /control/api/pericope/author-acq/review-packets`
- `POST /control/api/pericope/author-acq/review-packets/{id}/approve`
- `POST /control/api/pericope/author-acq/review-packets/{id}/reject`
- `POST /control/api/pericope/author-acq/review-packets/{id}/defer`

Exit criteria:

- operator can act on packets without terminal access
- actions are auditable
- UI cannot directly mark production completion

### Phase 6: Publication Handoff And Public Verification

Deliverables:

- production publication packet
- governed upload/sync checklist
- production activation checklist
- public verification runner
- ledger status finalizer guarded by evidence

Candidate commands:

```bash
author-acq prepare-publication --author <slug> --dry-run
author-acq verify-public --author <slug>
author-acq finalize-status --author <slug> --requires-public-verification <packet-id>
```

Exit criteria:

- production work stays inside Fortress Phronesis deployment policy
- public verification evidence exists before complete status is written
- failed public verification produces a repair packet, not a false complete

## First Buildable Slice

Build Phase 0 and a narrow Phase 1 before any source downloading or control UI.

The first useful milestone is:

```bash
python3 scripts/author-acq.py audit-tracker --dry-run
author-acq audit-coverage --author hermes_trismegistus --dry-run
author-acq audit-coverage --status "texts downloaded; index built; runtime wired" --dry-run
```

Why this slice first:

- it attacks the real tracker backlog
- it produces useful work without production risk
- it exercises ledger sync, status vocabulary, local work extraction, and report
  generation
- it creates the packet shapes that `fortress.local` can later display

## Testing Plan

Required tests:

- ledger JSON validation tests
- ledger sync/drift tests
- status vocabulary tests
- duplicate author/name normalization tests
- current-count regression fixture
- local work extraction tests
- title alias normalization tests
- coverage gap classification tests
- source-card schema tests
- download-plan dry-run tests
- metadata generation dry-run tests
- index build command construction tests
- local verification response parsing tests
- public verification response parsing tests
- approval gate tests proving no write/publish action executes without approval

## Observability

Track:

- job run duration
- authors scanned
- works found locally
- candidate gaps created
- source candidates created
- source cards approved/rejected/deferred
- downloads attempted
- normalization failures
- index build failures
- local verification failures
- public verification failures
- ledger validation failures
- queue backlog by status
- review backlog by packet type

Logs must not include API keys, bearer tokens, cookies, private prompts,
authorization headers, or unrelated private notes.

## Definition Of Done

The first complete author-acquisition-agent release is done when:

- the tracker audit reproduces ledger counts and flags legacy/incomplete states
- coverage audit finds missed-publication candidates for at least one acquired
  or partially acquired author
- source cards can be prepared in dry-run form
- approved local acquisition can run for one bounded author/work
- local metadata, index, profile, and retrieval verification pass
- `fortress.local` can show review packets or a compatible JSON export exists
- a publication handoff packet can be generated without executing production
  changes
- public verification can finalize an author only when evidence passes
- both acquisition ledgers validate after any proposed write
- no new public route, host port, service, env var, or deployment path was
  introduced without the required architecture and deployment-lock updates

## Open Questions

- Should first persistence be JSON artifacts under Fortress Phronesis or MySQL
  operator tables?
- Should the first coverage audit target all legacy runtime-wired authors or
  just one author with known broad coverage such as Hermes Trismegistus?
- Which source providers are approved for automatic metadata lookup on day one?
- What exact approval identity should be recorded for local-only operator
  actions before full auth integration exists?
