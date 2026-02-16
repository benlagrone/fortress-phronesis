# JSON Inventory and Migration Plan

## Purpose
Create a controlled, auditable plan to inventory all JSON files across the workspace, decide what should migrate to a database, and reduce hidden or duplicated JSON sprawl.

## Scope
Repositories in this workspace:

1. `AugustineCorpus`
2. `AugustineCorpusGateway`
3. `AugustineFE`
4. `AugustineService`
5. `fortress-phronesis`
6. `Model_Discernment_Engine`
7. Top-level `docs/`

## Target Outcomes

1. Complete JSON inventory with ownership and usage mapping.
2. Clear keep/migrate/archive decision for each JSON artifact.
3. Staged migration plan for domain metadata to DB.
4. Guardrails to prevent new JSON drift.

## Operating Principles

1. No destructive cleanup during inventory.
2. Quarantine before deletion.
3. Idempotent ingestion and migration steps.
4. Backward-compatible cutover with rollback path.
5. Keep source of truth explicit for every data domain.

## Phase 1: Read-Only Inventory

1. Enumerate all JSON files including hidden directories (exclude `.git`, `node_modules`, virtualenvs).
2. Capture metadata for each file:
   1. Path
   2. Repo/service
   3. Size
   4. Last modified time
   5. Git tracked/untracked
   6. Hidden-path flag
   7. JSON validity
3. Map each file to:
   1. Owning service/team
   2. Current readers/writers
   3. Runtime criticality
4. Produce `json_inventory.csv` and a review snapshot.

## Phase 2: Classification

Classify each JSON into exactly one primary bucket:

1. `config` (static runtime settings)
2. `domain_data` (business/content metadata)
3. `generated` (derived artifacts)
4. `cache` (ephemeral accelerators)
5. `test_output` (test/report data)
6. `legacy_or_recovery` (historical or emergency recovery files)
7. `secret_risk` (contains keys/tokens/secrets)

## Decision Tree: Keep vs Migrate vs Archive

1. Does it contain secrets or credentials?
   1. Action: move to env/secret manager; do not keep as data JSON.
2. Is it generated, cache, or test output?
   1. Action: do not migrate to DB; keep as artifact/temp output or prune policy.
3. Is it static runtime config, small, and tied to deploy cycle?
   1. Action: keep in Git JSON.
4. Is it domain data used by multiple interfaces/services, needs query/filtering, or changes independent of deploy?
   1. Action: migrate to DB.
5. Is it large text corpus/blob-style content?
   1. Action: keep in files/object storage; migrate only structured metadata to DB.

## Migration Trigger Rule

Migrate JSON to DB if at least 2 of these are true:

1. Used by 2 or more interfaces/services.
2. Requires filtering/sorting/search beyond key lookup.
3. Updated without app deploy.
4. Needs audit trail/versioning.
5. Record count is large or growing rapidly.

## Initial Decisions (Current State)

1. `AugustineCorpus/texts/*_texts/book_metadata.json`
   1. Classification: `domain_data`
   2. Decision: migrate to DB (high priority)
2. `AugustineCorpus/author_index.json`
   1. Classification: `config` plus routing/access policy
   2. Decision: keep in Git initially; optional DB mirror later
3. `AugustineCorpus/chapter_formats.json`
   1. Classification: `config`
   2. Decision: keep in Git
4. JSON/JSONL test outputs and reports
   1. Classification: `test_output` or `generated`
   2. Decision: do not migrate
5. Recovery/legacy JSON in hidden folders
   1. Classification: `legacy_or_recovery`
   2. Decision: quarantine and review

## Phase 3: DB Migration Waves

1. Wave 1: Inventory and decision sign-off
2. Wave 2: Pilot import for `book_metadata.json`
3. Wave 3: Add DB-backed read APIs with JSON fallback
4. Wave 4: Cut clients to DB-first, keep rollback
5. Wave 5: Archive redundant JSON after one stable release cycle

## Proposed DB Model (Metadata Focus)

1. `authors`
   1. author identity and canonical slug
2. `books`
   1. book identity tied to author
3. `book_metadata`
   1. normalized fields needed by clients
4. `book_metadata_raw`
   1. original payload for traceability
5. `ingest_runs`
   1. checksums, counts, errors, timestamps

## Validation and Safety Checks

1. JSON schema validation on source files.
2. Pre/post migration row-count parity per author.
3. Checksum tracking for source file integrity.
4. Idempotent importer re-run safety.
5. Dual-read fallback until parity and latency thresholds are met.

## Guardrails to Prevent Drift

1. CI check for JSON validity in tracked config/domain files.
2. CI rule to block new JSON outside allowlisted paths.
3. Scheduled monthly inventory diff report.
4. Quarantine-first policy for unknown JSON.

## Deliverables

1. `json_inventory.csv`
2. `json_decision_matrix.csv`
3. Migration runbook
4. Cutover checklist with rollback criteria
5. Post-cutover audit report

## Open Decisions

1. DB engine choice for metadata (`mysql` reuse vs `postgres` adoption).
2. Final source-of-truth policy for `author_index.json`.
3. Retention window for quarantined JSON before permanent removal.
