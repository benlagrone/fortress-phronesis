# Citation, Cross-Reference, and Author Discovery Agent Plan

**Status:** planned  
**Owner surface:** Fortress Phronesis docs and deployment control plane  
**Runtime target:** Fortress LAN background jobs, with review in the local control plane  
**Current source of truth:** MySQL plus the existing author-acquisition ledgers  
**Deployment note:** This plan does not add a deployed service, public route, host port, or environment variable by itself.

## Purpose

PericopeAI should turn citations and references into durable product
infrastructure. The system should discover how acquired works relate to one
another, identify outside authors and works that are not yet acquired, and pass
reviewed candidates into the author-acquisition process.

The design is evidence-first:

1. The citations agent extracts and normalizes references.
2. The cross-reference agent builds typed relationships from resolved evidence.
3. The author discovery agent identifies non-acquired authors and works.
4. The author acquisition agent receives reviewed leads and advances only
   through the existing acquisition gates.

## Product Boundary

This is not a replacement for normal chat. It is a background enrichment and
operator workflow that improves:

- reader-facing citations and related-passages surfaces
- corpus cross-reference quality
- author acquisition prioritization
- provenance and auditability

Normal PericopeAI chat may consume reviewed outputs, but the initial extraction
and acquisition decisions happen outside the live request path.

## Control-Plane Shape

Use a two-plane model:

- `fortress.local`: operator-facing review and control surface
- `fortress.lan`: background execution plane for long-running jobs
- `pericopeai.local`: reader/chat application surface that consumes approved
  citation and cross-reference data

The intended communication loop is:

```text
PericopeAI corpus and metadata
  -> fortress.lan citation/reference jobs
  -> resolved references and candidate edges
  -> fortress.local review inbox
  -> user approval or rejection
  -> author acquisition queue or reader-facing reference data
```

The agent must not silently publish new authors, mutate production acquisition
state, or ingest third-party text because it found a reference.

## Agent Responsibilities

### Citations Agent

Owns the question: "What is this reference, and where is the evidence?"

Responsibilities:

- extract explicit citations, quoted text, named authors, named works,
  bibliographic mentions, and likely allusions
- normalize references to canonical author, work, passage, edition, and
  external identifiers where available
- classify acquired, queued, rejected, and unknown author/work status
- store evidence spans from the source text
- attach provenance, extraction method, confidence, and run version

The citations agent is the evidence layer. Other agents may not create durable
edges or acquisition leads unless a citation/reference record exists with
evidence and provenance.

### Cross-Reference Agent

Owns the question: "How are these works related?"

Responsibilities:

- consume resolved citation/reference records
- create typed relationships such as:
  - direct citation
  - quoted text
  - author mention
  - work mention
  - allusion
  - shared theme
  - contrast
  - reception
  - influence
  - doctrinal parallel
- require anchors on both sides when the relationship is between two passages
- preserve confidence, review status, and extraction method on every edge
- support reverse lookup, such as "who references Augustine?" or "which authors
  cite Proverbs?"

The cross-reference agent should not invent clever but unsupported connections.
If the evidence is weak, it remains a candidate edge for review.

### Author Discovery Agent

Owns the question: "Does this reference point to someone PericopeAI does not
have?"

Responsibilities:

- find resolved references where the target author or work is not acquired
- dedupe candidates across spelling variants and external identifiers
- rank candidates by corpus relevance, frequency, bridge value, and available
  source metadata
- create reviewable leads for the acquisition workflow
- distinguish inbound reception from outbound influence:
  - inbound reception: outside authors reference acquired authors
  - outbound influence: acquired authors reference non-acquired authors
  - peer cluster: multiple acquired authors reference the same non-acquired
    author
  - bridge candidate: one non-acquired author connects otherwise separate
    traditions

The author discovery agent is metadata-first. It creates acquisition leads; it
does not acquire source text.

### Author Acquisition Agent

Owns the question: "Should this author enter the acquisition queue?"

Responsibilities:

- consume reviewed author discovery leads
- check source availability, rights posture, portrait/media requirements, and
  publication readiness
- update `AugustineService/metadata/author_acquisition.json` and
  `fortress-phronesis/docs/author_acquisition.json` only after explicit
  approval
- preserve the process contract in
  `docs/author-acquisition-process.md`: local acquisition, local runtime
  wiring, production corpus publication, production activation, and public
  verification are all required

The acquisition agent is an operator assistant, not an autonomous publisher.

## Data Model

Phase 1 should use relational tables or MySQL-backed records. A graph database
is optional later and must remain a derived read model unless explicitly
promoted.

### `reference_extraction_run`

Tracks reproducible extraction batches.

Required fields:

- `run_id`
- `agent_version`
- `source_scope`
- `started_at`
- `finished_at`
- `status`
- `input_corpus_version`
- `normalization_version`
- `notes`

### `resolved_reference`

Stores one extracted and normalized reference.

Required fields:

- `reference_id`
- `run_id`
- `source_passage_id`
- `source_author_slug`
- `source_work_id`
- `reference_type`
- `raw_text`
- `normalized_target_type`
- `normalized_target_id`
- `target_author_slug`
- `target_work_id`
- `target_status`
- `evidence_start`
- `evidence_end`
- `evidence_text`
- `provenance`
- `confidence`
- `review_status`
- `created_at`

`target_status` values should include:

- `acquired`
- `queued`
- `rejected`
- `non_acquired`
- `unknown`

### `cross_reference_edge`

Stores durable or candidate relationship edges.

Required fields:

- `edge_id`
- `source_passage_id`
- `target_type`
- `target_id`
- `relationship_type`
- `supporting_reference_id`
- `evidence_source_span`
- `evidence_target_span`
- `confidence`
- `review_status`
- `extraction_method`
- `run_id`
- `created_at`

### `author_discovery_lead`

Stores reviewable acquisition leads.

Required fields:

- `lead_id`
- `candidate_author_name`
- `candidate_work_title`
- `candidate_author_status`
- `relationship_summary`
- `primary_acquired_author_slug`
- `primary_acquired_work_id`
- `supporting_reference_ids`
- `external_ids_json`
- `rights_status`
- `source_availability_status`
- `priority_score`
- `priority_reason`
- `review_status`
- `next_action`
- `created_at`
- `updated_at`

Example:

```json
{
  "candidate_author_name": "Cicero",
  "candidate_work_title": "De Officiis",
  "candidate_author_status": "non_acquired",
  "relationship_summary": "Referenced by an acquired Augustine passage.",
  "primary_acquired_author_slug": "augustine",
  "primary_acquired_work_id": "confessions",
  "supporting_reference_ids": ["ref_123"],
  "external_ids_json": {
    "wikidata": "Q1541",
    "openalex": "..."
  },
  "rights_status": "public_domain_candidate",
  "source_availability_status": "metadata_found",
  "priority_score": 0.82,
  "priority_reason": "Bridge candidate connected to multiple acquired works.",
  "review_status": "pending_review",
  "next_action": "review_for_author_acquisition"
}
```

## External Resolution Sources

Use external sources for metadata and identifiers before attempting text
acquisition:

- OpenAlex for scholarly works and citation graph metadata
- Crossref for DOI and publication metadata
- Wikidata for canonical entity reconciliation
- Open Library for books and author/work metadata
- Gutendex and Project Gutenberg for public-domain text candidates
- Wikimedia Commons for portrait/media candidates
- Hugging Face datasets only when a dataset has clear provenance and rights
  posture

External records should become metadata evidence and candidate sources, not
automatic corpus imports.

## Review Surface

`fortress.local` should expose an operator inbox with at least these views:

- citation extraction run history
- unresolved or low-confidence references
- candidate cross-reference edges
- non-acquired author leads
- duplicates and canonicalization conflicts
- leads ready for author-acquisition review

Core actions:

- approve reference
- reject reference
- merge duplicate target
- mark needs source review
- mark needs rights review
- approve author lead for acquisition queue
- defer author lead
- reject author lead

Every operator action should preserve:

- actor
- timestamp
- prior state
- new state
- reason or note

## API and Job Boundaries

Initial surfaces should be internal or operator-only.

Candidate job commands:

- `citation-scan --scope author:<slug>`
- `citation-scan --scope work:<work_id>`
- `crossref-build --run-id <run_id>`
- `author-leads-build --run-id <run_id>`
- `author-leads-export --status approved`

Candidate operator APIs:

- `GET /control/api/pericope/references/runs`
- `GET /control/api/pericope/references/pending`
- `POST /control/api/pericope/references/{reference_id}/review`
- `GET /control/api/pericope/crossrefs/pending`
- `POST /control/api/pericope/crossrefs/{edge_id}/review`
- `GET /control/api/pericope/author-leads`
- `POST /control/api/pericope/author-leads/{lead_id}/review`

If any endpoint is exposed beyond local/operator control, it must enforce
authentication, authorization, rate limits, redaction, and scope limits.

## Reader-Facing Contract

PericopeAI should only show reviewed or confidence-gated outputs.

Reader-facing surfaces may include:

- related passages
- related authors and works
- "referenced by" reverse lookup
- citation provenance detail
- evidence snippets

Reader-facing surfaces should not expose:

- raw graph topology
- internal ontology definitions
- unreviewed acquisition leads
- private operator notes
- third-party source text that has not passed rights review

## Implementation Phases

### Phase 0: Contract and Fixtures

Goal: define the schema and prove the extraction contract against known examples.

Deliverables:

- schema migration draft or local fixture schema
- extraction fixtures for direct citation, work mention, author mention,
  allusion, and false positive
- canonical target-status vocabulary
- operator review status vocabulary
- fixture-based tests for evidence spans and normalization

Exit criteria:

- every extracted reference has source text evidence
- every candidate edge points to a supporting reference
- non-acquired targets are marked without entering the acquisition ledgers

### Phase 1: Citations Agent

Goal: create normalized references from acquired corpus passages.

Deliverables:

- background job for bounded citation scans
- canonicalization adapters for internal catalog, Wikidata, Open Library,
  OpenAlex, Crossref, and Gutendex metadata
- relational persistence for extraction runs and resolved references
- confidence and review-status tracking
- local CLI report for pending references

Exit criteria:

- known acquired passages produce expected references
- ambiguous names remain reviewable instead of over-resolved
- no live chat path depends on the job

### Phase 2: Cross-Reference Agent

Goal: turn resolved references into typed relationship edges.

Deliverables:

- edge builder from reviewed and confidence-gated references
- reverse lookup by author, work, and passage
- edge review states
- export or API shape for PericopeAI reference panels

Exit criteria:

- related-passages and related-authors queries return evidence-backed rows
- each edge has relationship type, evidence, confidence, and run version
- deleting or rejecting a reference invalidates dependent candidate edges

### Phase 3: Author Discovery Agent

Goal: identify non-acquired authors and works from the reference graph.

Deliverables:

- lead builder for targets with `target_status` of `non_acquired` or `unknown`
- dedupe and external-ID reconciliation
- priority scoring
- review inbox data contract
- export format for author acquisition review

Exit criteria:

- leads are explainable by supporting references
- duplicate author/work variants collapse into a single candidate where safe
- author-acquisition ledgers are not modified automatically

### Phase 4: Operator Review in `fortress.local`

Goal: make the workflow usable by the owner.

Deliverables:

- local control-plane pages or panels for pending references, edges, and leads
- approve/reject/defer actions
- run history and failure visibility
- filtered views for high-priority leads and rights-review needs

Exit criteria:

- the owner can answer "why is this author recommended?"
- every approval is auditable
- rejected/deferred leads stop reappearing without new evidence

### Phase 5: Author Acquisition Handoff

Goal: connect approved leads to the existing acquisition process.

Deliverables:

- approved lead export into the author-acquisition queue format
- ledger update tool with dry-run and diff output
- checks that both acquisition ledgers stay synchronized
- JSON validation after every proposed ledger update
- status strings that preserve production publication and public verification
  gates

Exit criteria:

- a lead can become a queued author only after approval
- both ledgers update together
- the existing acquisition process remains the authority for completion

### Phase 6: Reader-Facing Consumption

Goal: expose reviewed reference intelligence inside PericopeAI without adding
live-path fragility.

Deliverables:

- API shape for reviewed related references
- frontend panel for related passages/authors/works
- provenance detail view
- tests for absent, pending, rejected, and approved reference states

Exit criteria:

- chat remains functional if the reference layer is unavailable
- users see evidence, not raw internal graph structures
- unreviewed acquisition leads never appear in the reader UI

## Observability

Track:

- extraction run count and duration
- references extracted per run
- unresolved target count
- low-confidence reference count
- cross-reference edges created
- edges rejected or invalidated
- author leads created
- author leads approved, rejected, deferred, and rights-review flagged
- duplicate merge count
- external resolver failures
- queue backlog by review status

Logs must avoid raw private prompts and secrets. Evidence snippets may be stored
only when they come from corpus/source text that is allowed in the relevant
operator context.

## Testing

Required test groups:

- extraction fixtures for direct citations and false positives
- canonicalization tests for ambiguous author and work names
- evidence-span tests proving offsets map to source text
- edge-builder tests requiring a supporting reference
- author-lead dedupe tests
- rights-status and source-availability tests
- ledger dry-run tests proving both acquisition files update together
- JSON validation tests for ledger output
- API authorization tests for operator endpoints
- reader-facing tests proving unreviewed leads are hidden

## Guardrails

- No cross-reference edge without evidence and provenance.
- No acquisition lead without supporting reference IDs.
- No ledger mutation without explicit review approval.
- No production publication without the author-acquisition process gates.
- No public route or host port without deployment-lock updates.
- No graph database promotion without a separate architecture decision and
  deployment change.
- No third-party text ingestion without rights review.

## Open Questions

- Which local control-plane project owns the first `fortress.local` review UI:
  `local_tools`, `fortress-lan`, or a Pericope-specific panel?
- Should the first persistence pass live in the PericopeAI MySQL database or a
  separate operator database on Fortress LAN?
- What confidence threshold is high enough for reader-facing display without
  manual review?
- Should author discovery leads be ranked globally, per tradition, or per
  acquired author cluster?
- Which external identifiers are mandatory before a non-acquired author can be
  queued?
