# Roadmap Recovery Ledger (Linked Backlog)

Purpose: capture recovered and high-priority requests in one append-only backlog linked to the canonical roadmap so requests are not lost across partial edits, branch drift, or untracked docs.

## Canonical Links

- Primary roadmap: [PericopeAI Semantic Versioned Feature Roadmap](roadmap.md)
- Deployment strategy: [PericopeAI Deployment (Control Plane)](pericopeai-deployment.md)
- Operating rules: [Developer Guide](developer-guide.md)

## Recovered Items

| ID | Item | Target | Status | Canonical Link |
| --- | --- | --- | --- | --- |
| UI-001 | Remove `Mode` selector from chat controls | v1.1.3 | Completed | [roadmap.md](roadmap.md#v113--augustine-frontend-control-simplification) |
| UI-002 | Remove `Test Memory` button from chat controls | v1.1.3 | Completed | [roadmap.md](roadmap.md#v113--augustine-frontend-control-simplification) |
| UI-003 | Combine persona selector into author context element as one panel | v1.1.3 | Completed | [roadmap.md](roadmap.md#v113--augustine-frontend-control-simplification) |
| UI-004 | Mobile viewport fit: message list scrolls independently, input pinned | v1.1.3 | Completed | [roadmap.md](roadmap.md#v113--augustine-frontend-control-simplification) |
| UI-005 | Bible-author voice guardrail to prevent first-person divine-speaker drift | v1.1.3 | Completed | [ui-005-bible-author-guardrail-public-20260330.md](../tests/ui-005-bible-author-guardrail-public-20260330.md) |
| UI-006 | Chat request lifecycle states and explicit timeout/error UX (`401`,`403`,`504`) | v1.1.4 | Completed | [ui-006-ui-007-public-verification-20260331.md](../tests/ui-006-ui-007-public-verification-20260331.md) |
| UI-007 | Responsive layout: mobile keeps single-column chat format; large desktop uses right-side context/references panel; mobile keeps input pinned while page can scroll to citations | v1.1.4 | Completed | [ui-006-ui-007-public-verification-20260331.md](../tests/ui-006-ui-007-public-verification-20260331.md) |
| MEM-001 | Purposeful conversational continuity: explicit session state, rolling summaries, durable relationship memory, and intake-as-thread seed | v1.2.2 | Planned | [roadmap.md](roadmap.md#v122--purposeful-conversation-state--relationship-memory) |
| DEP-001 | Enforce release discipline (code/data/full reindex separation) | v1.1.x ops | Active | [pericopeai-deployment.md](pericopeai-deployment.md#deployment-discipline-addendum-authoritative-for-strategy-changes) |
| DEP-002 | Mandatory preflight/smoke/rollback gates for prod deploys | v1.1.x ops | Active | [developer-guide.md](developer-guide.md) |
| DEP-003 | FE/API port contract must be one value everywhere (current conflict: `13080` vs `3000`) | v1.1.x ops | Closed | [release-runbook-prod-v1.1.2.md](release-runbook-prod-v1.1.2.md) |
| SVC-001 | Serviceized persona deploy model (`service_id` / `service_version`) | v1.3.1 | Completed | [roadmap.md](roadmap.md#v131--serviceized-persona-deployment-x-as-a-service) |
| SVC-001A | Canonical author-scoped index + restart helper for additive data deploys | v1.3.1 Phase A closeout | Completed | [pericopeai-deployment.md](pericopeai-deployment.md#d-data-release-default-author-scoped-indexing) |
| SVC-001B | Canonical service-version pointer promotion + rollback helper/workflow | v1.3.1 Phase B start | Completed | [pericopeai-deployment.md](pericopeai-deployment.md#h-service-version-pointer-controls-svc-001b) |
| SVC-001B-PUB | Public edge alignment for `service-version` history route | v1.3.1 Phase B closeout | Completed | [pericope-api-public-deploy-20260327.md](../tests/pericope-api-public-deploy-20260327.md) |
| SVC-002 | MDE promotion gate as mandatory production control | v1.3.1 Phase C | Completed | [roadmap.md](roadmap.md#v131--serviceized-persona-deployment-x-as-a-service) |
| XREF-001 | Bootstrap cross book/author cross-referencing API surfaces (`/crossrefs/books`, `/crossrefs/books/{book_id}`, `/crossrefs/authors/{author_slug}`) from canonical metadata map | v1.3.0 start | Completed | [roadmap.md](roadmap.md#v130) |
| SCR-001 | Verse-level scripture bundle for cited Bible text: original-language source, canonical English translations, lexical notes, and optional patristic/commentary expansion surfaced from References and reusable in chat context | v1.3.6 | Completed | [roadmap.md](roadmap.md#v136--verse-bundle-and-original-language-insight) |
| RAG-001 | Repo-scoped local RAG workflow for engineering support | Dev tooling | Active | [dev_rag.md](dev_rag.md) |
| DOC-001 | Keep legacy docs; additive updates only; no silent replacement | Continuous | Active | [developer-guide.md](developer-guide.md#11-documentation-rules) |
| REL-001 | Cross-project release commitment contract for Pericope, Solomonic, MDE, and Latin RAG | v1.1.3 | Active | [release-commitment-v1.1.3-all-tracks.md](release-commitment-v1.1.3-all-tracks.md) |
| OPS-OLLAMA-001 | Production Ollama route must use the Fortress UniFi/IPsec endpoint and reject local-only container/host endpoints in deploy preflight | v1.4.0-ops carryover | Published 2026-06-12; keep monitored | [roadmap.md](roadmap.md#current-roadmap-control-state-2026-06-22) |
| OPS-STATE-001 | Reconcile divergent/dirty `fortress-phronesis` local checkout against published `origin/main` before relying on local branch state | Roadmap control gate | Open | [roadmap.md](roadmap.md#unfinished-publication--merge-gate) |
| OPS-STATE-002 | Publish or supersede unpublished local work in `Solomonic_Seals` | Roadmap control gate | Completed 2026-06-22 | [roadmap.md](roadmap.md#current-roadmap-control-state-2026-06-22) |
| OPS-STATE-003 | Classify uncommitted MDE and Solomonic changes as publish, keep-local, split, or discard by explicit request | Roadmap control gate | Completed 2026-06-22 | [roadmap.md](roadmap.md#current-roadmap-control-state-2026-06-22) |
| OPS-STATE-004 | Create or choose a remote for `pericopeai-mobile-app`, set upstream, and push local mobile commit `b357260` | Roadmap control gate | Blocked: no remote repository exists | [roadmap.md](roadmap.md#unfinished-publication--merge-gate) |
| ASK-PROV-001 | First-pass Ask Proverbs runtime belongs to Pericope API/frontend and must stay out of the Solomonic Clock guided-prompts path | v1.3.x / v1.4 carryover | Published in Pericope and Solomonic repos | [roadmap.md](roadmap.md#current-roadmap-control-state-2026-06-22) |
| MOBILE-VOICE-001 | Mobile v1 scope includes auth, single-author chat, user voice-to-text, author text-to-voice, conversational mode, foldable layout, and Android TV layout | v1.4.1 / v1.5.0 planning | Planning docs published; mobile implementation committed locally, remote pending | [roadmap.md](roadmap.md#current-roadmap-control-state-2026-06-22) |

## Immediate Execution Order

1. [Completed 2026-03-03] Resolve and lock one frontend host port contract everywhere (`compose`, lock script, runbooks, nginx).
2. [Completed 2026-03-03] Ship v1.1.3 UI simplification end-to-end in code and release notes.
3. [Completed 2026-03-27] Close `v1.3.1` after successful public deploy alignment and public `200` verification for both service-version endpoints.
4. [Completed 2026-03-30] Close remaining `v1.1.3` UI carry-over by landing `UI-005` (Bible-author voice guardrail).
5. [Completed 2026-03-31] Close `v1.1.4` carry-over `UI-006` (request states + `401` / `403` / `504` handling).
6. [Completed 2026-03-31] Close `v1.1.4` carry-over `UI-007` (desktop right-side context/references panel while preserving mobile behavior).
7. [Completed 2026-03-31] All `v1.1.x` UI carry-over work is closed; forward roadmap work may resume.
8. [Completed 2026-04-04] Close `v1.3.0` bootstrap cross-reference surface (`XREF-001`) and `v1.3.3` public graph boundary (`XREF-002`).
9. [Completed 2026-04-06] Close `v1.3.4` Stage 1/Stage 2/Stage 3 text-first graph pipeline (normalized passages + explicit reference extraction + semantic neighbors).
10. [Completed 2026-04-11] Close `v1.1.6` saved author preferences (authenticated favorites + default author persistence with signed-in launch/new-chat preselection and degraded-default handling).
11. [Blocked 2026-06-22] Pause new `v1.3.7` / `v1.4.0` implementation until the publication/merge gate below is cleared.
12. [Completed 2026-06-22] Publish roadmap rectification and audit from a clean Fortress worktree.
13. [Completed 2026-06-22] Push Solomonic guided prompt, mobile readiness, launch contract, and deployment promotion work.
14. [Completed 2026-06-22] Split and push MDE candidate workflow source changes and refreshed generated report artifacts.
15. [Current 2026-06-22] Reconcile divergent/dirty `fortress-phronesis` local `main` against `origin/main`.
16. [Blocked 2026-06-22] Create or choose a remote for `pericopeai-mobile-app`, set upstream, and push `b357260`.

## Update Rule

- Add new requests here first, then map them into the semantic roadmap release section.
- Do not delete prior entries; update `Status` and add canonical links as work lands.
- When a roadmap item is too broad for one clean execution pass, split it into smaller named sub-commitments here before continuing work.
- Status reporting should use the active sub-commitment label, not only the parent umbrella version.
- If the same umbrella label appears across multiple verified iterations, stop and create dated closeout slices instead of repeating the umbrella unchanged.
