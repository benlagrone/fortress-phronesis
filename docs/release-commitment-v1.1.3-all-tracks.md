# Release Commitment — v1.1.3 (All Tracks)

## Release Identity

- Release train: `v1.1.3`
- Date: `2026-02-28`
- Scope type: cross-project commitment baseline
- Canonical owner: `fortress-phronesis` control-plane docs

## Purpose

Define one explicit commitment contract for this release across:

1. Pericope core (API/FE/deploy)
2. Solomonic Clock
3. Model Discernment Engine (MDE)
4. Latin RAG Translator

This document is binding for scope control, release gates, and sign-off.

## Canonical References

- [Semantic Roadmap](roadmap.md)
- [Roadmap Recovery Ledger](roadmap-recovery-ledger.md)
- [Pericope Deployment Guide](pericopeai-deployment.md)
- [Developer Guide (Rules)](developer-guide.md)
- [Acceptance Test + Demo Guide v1.1.3](acceptance-demo-guide-v1.1.3.md)

## Global Non-Negotiables

1. No destructive doc replacement; additive updates only.
2. No ad-hoc env overrides for production deploy behavior.
3. Every deploy path must be reproducible from docs.
4. Every committed change must have a rollback path.
5. Release is blocked if port/environment contracts conflict across compose/runbooks.

## Track Commitments

### A) Pericope Core (API + Frontend + Deploy)

Committed for this release:

1. Ship `v1.1.3` UI simplification:
   - remove `Mode` selector
   - remove `Test Memory` button
   - combine persona selector into author context element
2. Mobile behavior guard:
   - chat area remains viewport-focused
   - input/send controls remain visible at bottom during normal chat flow
3. Start cross book/author cross-referencing (bootstrap slice):
   - deterministic API surfaces backed by canonical metadata map:
     - `/api/v1/crossrefs/books`
     - `/api/v1/crossrefs/books/{book_id}`
     - `/api/v1/crossrefs/authors/{author_slug}`
4. Resolve FE host-port contract drift (`13080` vs `3000`) by selecting one canonical value and aligning:
   - compose
   - deploy-lock script
   - release runbook
   - nginx upstream docs
5. Run mandatory preflight + smoke + rollback gates before sign-off.

Evidence required:

- FE screenshots (mobile + desktop)
- `git diff` for `AugustineFE/src/App.js`, `AugustineFE/src/App.css`
- lock-check output
- smoke probe outputs (`healthz`, direct chat, public chat)

### B) Solomonic Clock

Committed for this release:

1. Execute Phase 1 foundation slice (no Phase 2 expansion yet):
   - scripture mapping baseline complete for in-scope set
   - numbering normalization pass
   - validation tooling runnable with documented command
2. Produce one audited artifact set:
   - updated mapping file(s)
   - validation report output
   - source/citation trace list

Evidence required:

- updated mapping artifacts in repo
- validator command and output log
- short coverage summary (mapped vs pending)

### C) Model Discernment Engine (MDE)

Committed for this release:

1. Define promotion-gate schema and minimum run contract for future `v1.3.1` enforcement:
   - `run_id`, `service_id`, `service_version`
   - model/provider + prompt version + dataset version
   - required metrics and thresholds
2. Produce baseline evaluation template and one sample run output.

Evidence required:

- schema/spec doc update
- sample eval artifact (JSON/CSV)
- threshold table with pass/fail criteria

### D) Latin RAG Translator

Committed for this release:

1. Lock and document translator deployment contract:
   - API endpoint contract
   - runbook path for prod
   - health/smoke checks
2. Align translator docs to central control-plane index and release discipline.

Evidence required:

- doc links verified
- successful health and one functional request example

## Out of Scope (This Release)

1. Full `v1.3.0` cross-reference graph implementation.
2. Full `v1.3.1` service API rollout.
3. Full mobile app build/release program.
4. Multi-tenant/platform marketplace features.

## Next Feature Commitment (Queued for Next Train)

### Pericope Core: Reference Fidelity and Cross-Author Linking

Committed for next feature train (post-`v1.1.3`):

1. Add inferred Bible references to the References panel when answer text cites scripture not present in retrieval metadata.
   - Example target behavior: Augustine answer mentioning `Genesis 2:16-17` shows `Genesis 2:16-17` as a reference row.
2. Add non-Bible cross-author/work inference from answer text and retrieval excerpts.
   - Example target behavior: if Socrates answer references Plato/Republic, a reference entry is created and can be opened.
3. Unify open behavior for inferred references:
   - `Open` resolves through local author/work catalog and loads `book` or `book_partial` content where available.
4. Add reference provenance labels in UI:
   - `retrieved` (from corpus metadata)
   - `inferred_from_answer`
   - `inferred_from_excerpt`
5. Add deterministic demo prompts and examples for non-Bible -> Bible and cross-author scenarios.

Evidence required:

- screenshot showing inferred scripture reference present in References panel for a non-Bible persona response.
- screenshot showing cross-author inferred reference (e.g., Socrates -> Plato) and successful `Open`.
- sample JSON artifact with extracted inferred references and provenance labels.
- updated acceptance/demo guide checklist covering inferred-reference cases.

External dependency policy:

1. Baseline implementation must use only internal corpus/catalog data (no external API required).
2. Optional external normalization sources (abbreviation/alias tables) are allowed only as additive enhancement after baseline passes.

## Release Gates (All Tracks Must Pass)

1. Scope gate: no unapproved expansion beyond commitments above.
2. Contract gate: no unresolved port/env contract conflicts.
3. Test gate: required smoke/validation outputs archived.
4. Docs gate: canonical docs updated in same change set.
5. Rollback gate: rollback procedure defined and executable.

## Sign-Off Checklist

- [ ] Pericope core commitments complete
- [ ] Solomonic commitments complete
- [ ] MDE commitments complete
- [ ] Latin RAG commitments complete
- [ ] Smoke/validation artifacts attached
- [ ] Rollback path verified
- [ ] Docs index + roadmap links verified

## Execution Snapshot (March 3, 2026)

### Pericope Core Gate Evidence

1. Contract gate (`13080` lock): PASS
   - Command: `bash scripts/verify-pericope-deploy-lock.sh`
   - Result: all lock assertions passed, including FE host port `13080`.
2. Chat smoke gate: PASS
   - Command: `python3 scripts/smoke-tests.py --base-url http://localhost:18000 --authors augustine,marcus_aurelius --max-wait 60 --timeout 60 --out tests/author-chat-smoke-visible.jsonl`
   - Result: `PASS (failures=0/2)`.
3. Crossref smoke gate (bootstrap mapped author): PASS
   - Command: `python3 scripts/smoke-crossrefs.py --base-url http://localhost:18000 --author moses --limit 20 --timeout 90 --out tests/crossrefs-smoke-visible.json`
   - Result: all crossref checks passed for bootstrap mapped author coverage.
4. Crossref route availability check: PASS
   - Command: `curl -sS -i -m 20 'http://localhost:18000/api/v1/crossrefs/books?limit=5'`
   - Result: `HTTP/1.1 200 OK`.

### Deployment Drift Resolved in This Cycle

1. Rebuilt and restarted API container from current source:
   - `docker compose -f fortress-phronesis/docker-compose.pericope.yml up -d --build pericopeai-api`
2. Rebuilt and restarted corpus container from current source:
   - `docker compose -f fortress-phronesis/docker-compose.pericope.yml up -d --build augustine-corpus-live`
3. Post-rebuild outcome:
   - `/api/v1/crossrefs/*` endpoints are live through API.

### Remaining Before Full Sign-Off

1. Crossref coverage breadth remains bootstrap-stage:
   - `--author augustine` currently returns zero mapped books in crossref smoke.
2. Rollback execution proof for this release is still pending.
3. Non-Pericope tracks (Solomonic, MDE, Latin RAG) still require their evidence artifacts.

## Decision Log

- Port contract decision (`13080` or `3000`): `13080`
- Last gate execution snapshot: `March 3, 2026`
- Release go/no-go: `TBD`
