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
| UI-005 | New Testament tuning guardrail to prevent first-person Jesus drift | v1.1.3 | Planned | [roadmap.md](roadmap.md#v113--augustine-frontend-control-simplification) |
| UI-006 | Chat request lifecycle states and explicit timeout/error UX (`401`,`403`,`504`) | v1.1.4 | Planned | [roadmap.md](roadmap.md#v114--immediate-ui-hardening-and-operator-clarity) |
| UI-007 | Responsive layout: mobile keeps single-column chat format; large desktop uses right-side context/references panel; mobile keeps input pinned while page can scroll to citations | v1.1.4 | Planned | [roadmap.md](roadmap.md#v114--immediate-ui-hardening-and-operator-clarity) |
| MEM-001 | Purposeful conversational continuity: explicit session state, rolling summaries, durable relationship memory, and intake-as-thread seed | v1.2.2 | Planned | [roadmap.md](roadmap.md#v122--purposeful-conversation-state--relationship-memory) |
| DEP-001 | Enforce release discipline (code/data/full reindex separation) | v1.1.x ops | Active | [pericopeai-deployment.md](pericopeai-deployment.md#deployment-discipline-addendum-authoritative-for-strategy-changes) |
| DEP-002 | Mandatory preflight/smoke/rollback gates for prod deploys | v1.1.x ops | Active | [developer-guide.md](developer-guide.md) |
| DEP-003 | FE/API port contract must be one value everywhere (current conflict: `13080` vs `3000`) | v1.1.x ops | Closed | [release-runbook-prod-v1.1.2.md](release-runbook-prod-v1.1.2.md) |
| SVC-001 | Serviceized persona deploy model (`service_id` / `service_version`) | v1.3.1 | Completed | [roadmap.md](roadmap.md#v131--serviceized-persona-deployment-x-as-a-service) |
| SVC-001A | Canonical author-scoped index + restart helper for additive data deploys | v1.3.1 Phase A closeout | Completed | [pericopeai-deployment.md](pericopeai-deployment.md#d-data-release-default-author-scoped-indexing) |
| SVC-001B | Canonical service-version pointer promotion + rollback helper/workflow | v1.3.1 Phase B start | Completed | [pericopeai-deployment.md](pericopeai-deployment.md#h-service-version-pointer-controls-svc-001b) |
| SVC-001B-PUB | Public edge alignment for `service-version` history route | v1.3.1 Phase B closeout | Completed | [pericope-api-public-deploy-20260327.md](../tests/pericope-api-public-deploy-20260327.md) |
| SVC-002 | MDE promotion gate as mandatory production control | v1.3.1 Phase C | Completed | [roadmap.md](roadmap.md#v131--serviceized-persona-deployment-x-as-a-service) |
| XREF-001 | Bootstrap cross book/author cross-referencing API surfaces (`/crossrefs/books`, `/crossrefs/books/{book_id}`, `/crossrefs/authors/{author_slug}`) from canonical metadata map | v1.3.0 start | In Progress | [roadmap.md](roadmap.md#v130) |
| SCR-001 | Verse-level scripture bundle for cited Bible text: original-language source, canonical English translations, lexical notes, and optional patristic/commentary expansion surfaced from References and reusable in chat context | v1.3.6 | Planned | [roadmap.md](roadmap.md#v136--verse-bundle-and-original-language-insight) |
| RAG-001 | Repo-scoped local RAG workflow for engineering support | Dev tooling | Active | [dev_rag.md](dev_rag.md) |
| DOC-001 | Keep legacy docs; additive updates only; no silent replacement | Continuous | Active | [developer-guide.md](developer-guide.md#11-documentation-rules) |
| REL-001 | Cross-project release commitment contract for Pericope, Solomonic, MDE, and Latin RAG | v1.1.3 | Active | [release-commitment-v1.1.3-all-tracks.md](release-commitment-v1.1.3-all-tracks.md) |

## Immediate Execution Order

1. [Completed 2026-03-03] Resolve and lock one frontend host port contract everywhere (`compose`, lock script, runbooks, nginx).
2. [Completed 2026-03-03] Ship v1.1.3 UI simplification end-to-end in code and release notes.
3. [In Progress] Run one disciplined release using required gates; archive outputs under `tests/` artifacts.
4. [In Progress 2026-03-16] Start v1.3.1 Phase A only (`service_id/service_version` + additive author-scoped deploy path).
5. [Completed 2026-03-18] Preserve active `service_version`/compatibility metadata on registry reseed and revalidate live `GET /api/v1/services*` surfaces after API rebuild.
6. [Completed 2026-03-21] Add canonical `scripts/reindex-author.sh` helper and move default author additions to one author-scoped index + restart + smoke path.
7. [Completed 2026-03-22] Add canonical `scripts/service-version.sh` helper, expose rollback-target metadata on `/api/v1/services/{service_id}/versions`, and verify live `augustine.en` promote/rollback pointer switches while restoring active `1.0.0` after proof.
8. [Completed 2026-03-27] Public `pericopeai.com` now serves `/api/v1/services/{service_id}/version` and `/api/v1/services/{service_id}/versions` after the control-plane GitHub Actions deploy path was added and verified.
9. [Completed 2026-03-26] Land local Phase C gate contract: required eval payload on promote, threshold + baseline enforcement, audited `/api/v1/services/{service_id}/promotions` history, and live approve/block/rollback proof on `augustine.en`.
10. [Completed 2026-03-26] Cut `v1.3.1` release scope harder: feature-complete locally; only public deploy alignment remains. No further `v1.3.1` feature expansion is allowed.
11. [Completed 2026-03-27] Close `v1.3.1` after successful public deploy alignment and public `200` verification for both service-version endpoints.

## Update Rule

- Add new requests here first, then map them into the semantic roadmap release section.
- Do not delete prior entries; update `Status` and add canonical links as work lands.
- When a roadmap item is too broad for one clean execution pass, split it into smaller named sub-commitments here before continuing work.
- Status reporting should use the active sub-commitment label, not only the parent umbrella version.
- If the same umbrella label appears across multiple verified iterations, stop and create dated closeout slices instead of repeating the umbrella unchanged.
