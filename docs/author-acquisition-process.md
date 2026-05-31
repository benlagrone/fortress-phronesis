# Author Acquisition Process

This document is the authoritative process contract for PericopeAI author acquisition.

It exists to close a gap that previously allowed local acquisition and runtime wiring to be treated as complete even when the production corpus payload had not been published to the host.

## Definition of Done

An author acquisition is complete only when all of the following are true:

1. Source texts and metadata are acquired locally.
2. The author is wired into the corpus/runtime stack locally.
3. The production corpus payload is published to the prod host.
4. Production author-scoped indexing and service restart are completed.
5. Public verification passes for catalog/profile/media/runtime behavior.

`runtime wired` by itself is not sufficient proof of completion.

## Required Stages

### 1) Local Acquisition

- Download or curate the source texts.
- Record works/notes in the acquisition ledger.
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
