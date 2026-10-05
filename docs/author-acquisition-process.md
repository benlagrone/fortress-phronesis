# Author Acquisition Process

This document is the authoritative process contract for PericopeAI author acquisition.

It exists to close a gap that previously allowed local acquisition and runtime wiring to be treated as complete even when the production corpus payload had not been published to the host.

## Definition of Done

An author acquisition is complete only when all of the following are true:

1. Source texts and metadata are acquired locally.
2. The acquisition ledger records the full set of acquired works mounted in the
   corpus for that author.
3. The author is wired into the corpus/runtime stack locally.
4. The production corpus payload is published to the prod host.
5. Production author-scoped indexing and service restart are completed.
6. Public verification passes for catalog/profile/media/runtime behavior.

`runtime wired` by itself is not sufficient proof of completion.
`Key Works` notes are optional metadata only. They must not substitute for the
full acquired-works inventory.
`public verification passed` is release completion, not a claim that the author
is bibliographically exhaustive forever.

## Required Stages

### 1) Local Acquisition

- Download or curate the source texts.
- Record all acquired works in the acquisition ledger.
- If `Key Works` notes are useful for editorial context, keep them separate from
  the full works inventory.
- Add catalog metadata and portrait metadata/assets as needed.

### 2) Local Runtime Wiring

- Mount the author text directory in `docker-compose.pericope.yml`.
- Wire any required index volume.
- Build the author index locally.
- Verify local retrieval and profile behavior.

### 3) Production Corpus Publication

This stage is mandatory for content-heavy author releases.

- Publish corpus text assets to the prod host using the corpus sync/upload path.
- If prebuilt index artifacts are part of the release, publish those artifacts too.
- Do not treat a git-based code deploy as proof that the corpus payload is present on prod.

Relevant references:

- [Prod Release Runbook v1.1.1](release-runbook-prod-v1.1.1.md)
- [PericopeAI Deployment Guide](pericopeai-deployment.md)
- [upload-corpus.sh](../scripts/upload-corpus.sh)
- [Publish Pericope Author Content workflow](../.github/workflows/publish-pericope-author-content.yml)

When the workstation does not hold the production SSH key, publish the
git-ignored text directories as a checksum-pinned temporary release asset and
dispatch `Publish Pericope Author Content`. The workflow accepts only
`texts/<author_slug>_texts/` archive members for the requested slugs, transfers
the payload with the protected production SSH credential, runs targeted
indexing, activates the locked Compose services, and enforces public catalog,
profile, portrait, and runtime checks. Delete the temporary release after the
workflow succeeds.

Keep `rebuild_indexes` enabled for normal acquisitions. Set it to `false` only
when retrying the same checksum-pinned payload after a post-index activation or
verification failure; the workflow then requires each persistent index store to
exist and still runs runtime retrieval plus all public checks.

### 4) Production Activation

- Run author-scoped indexing on prod for the changed author.
- Restart `augustine-corpus-live` and `pericopeai-api`.
- Re-sync author catalog data if the release changes profile/catalog payloads.

### 5) Public Verification

At minimum, verify:

- public `/api/v1/authors` presence when the author is meant to be public
- public `/api/v1/authors/{slug}/profile`
- public portrait/media path if one exists
- grounded retrieval/runtime behavior for the author when applicable

## Ongoing Coverage Audit

Completed and historically acquired authors remain subject to periodic coverage
audit.

- Coverage audit must check acquired authors for likely missing public-domain
  works using bounded bibliographic sources.
- Any likely misses must be emitted as reviewable `publication_gap_packet`
  items and optional source-card candidates.
- Coverage audit findings do not silently mutate ledgers or reclassify an
  author as incomplete. They reopen operator review for additional acquisition
  work.

## Status Vocabulary

Use status strings that make the production state explicit.

Recommended statuses:

- `pending`
- `next-up queued; pending text acquisition`
- `texts downloaded; pending prod corpus sync`
- `texts downloaded; prod corpus synced; pending index build`
- `texts downloaded; index built; pending prod corpus sync`
- `texts downloaded; prod corpus synced; index built; pending runtime wiring`
- `texts downloaded; prod corpus synced; index built; runtime wired; pending public verification`
- `texts downloaded; prod corpus synced; index built; runtime wired; public verification passed`

Legacy statuses such as `texts downloaded; index built; runtime wired` are now considered incomplete unless the ledger also records production corpus publication and public verification.

## Historical Compatibility Rule

Older acquisition entries may predate this hardened process and may not include explicit prod publication markers.

Treat those entries as historical records, not as sufficient proof that the author is complete on prod.

If an older entry is still live in current operations, update its status string and notes when prod corpus publication and public verification are re-confirmed.
When repairing older entries, also reconcile the ledger works inventory against
the corpus text directory or `book_metadata.json` so the tracker reflects all
acquired works, not only highlighted titles.
