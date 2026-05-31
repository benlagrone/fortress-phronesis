# Developer Guide (Rules of Operation)

Purpose: enforce disciplined, repeatable engineering and deployment behavior across PericopeAI control-plane operations.

## 1) Core Principles

1. Predictability over speed.
2. One canonical command path per operation.
3. No hidden state assumptions.
4. Every deploy must be reversible.
5. Documentation and runtime behavior must match.

## 2) Scope and Ownership

This repo is a control-plane.

1. It orchestrates sibling repos (`AugustineService`, `AugustineCorpus`, `AugustineFE`).
2. It does not own application business logic in those repos.
3. It does own deployment contracts, runbooks, and operational guardrails.

## 3) Non-Negotiable Rules

1. Do not delete or replace canonical docs unless explicitly approved.
2. Do not introduce ad-hoc deployment flows not captured in docs.
3. Do not use ad-hoc shell env overrides for deploy behavior.
4. Do not mutate running containers as a deployment strategy.
5. Do not change compose project name, network, or locked ports without explicit approval and matching doc updates.
6. Do not treat frontend `REACT_APP_*` variables as runtime settings; they are build-time inputs.

## 4) Canonical Paths

Prod:

1. Stack root: `/root/workspace/fortress-phronesis`
2. API repo: `/root/workspace/AugustineService`
3. Corpus repo: `/root/workspace/AugustineCorpus`
4. FE repo: `/root/workspace/AugustineFE`

Do not run deploy commands until path guard confirms expected root.

## 5) Environment Rules

1. `.env` files are authoritative:
   - `AugustineService/.env`
   - `AugustineCorpus/.env`
   - `AugustineFE/.env`
2. Never rely on top-level `fortress-phronesis/.env`.
3. FE builds must use:
   - `docker compose --env-file /root/workspace/AugustineFE/.env ...`
4. Clear shell overrides before FE build when in doubt:
   - `unset REACT_APP_AUGUSTINE_API_KEY REACT_APP_ENVIRONMENT REACT_APP_API_BASE_URL REACT_APP_ROOT_URL`

## 6) Release Types

1. Code Release:
   - API/FE/runtime logic changes.
   - Requires compose rebuild of affected services.
2. Data Release:
   - author/corpus/index updates.
   - default is author-scoped indexing and service restart.
   - author acquisition is not complete until prod corpus publication and public verification are recorded per `docs/author-acquisition-process.md`.
3. Full Reindex Release:
   - exceptional operation only.
   - must be explicit and documented.

## 7) Deployment Discipline

1. Always run lock check before deploy:
   - `bash scripts/verify-pericope-deploy-lock.sh`
2. Use canonical compose invocation:
   - `docker compose -p fortress-phronesis -f docker-compose.pericope.yml ...`
3. Build frontend with explicit FE env file:
   - `docker compose --env-file /root/workspace/AugustineFE/.env -p fortress-phronesis -f docker-compose.pericope.yml up -d --build pericopeai-frontend`
4. Use author-scoped indexing for regular author additions.
5. Do not run implicit full index as a routine update path.
6. For content-heavy author releases, publish corpus texts to prod through the corpus sync/upload path before marking an author complete.

## 8) Required Release Gates

A release is not complete unless all pass:

1. Preflight gate (lock + env checks).
2. Direct API health (`/api/healthz`).
3. Direct API chat probe (`/api/v2/chat` on host port).
4. Public chat probe (`https://pericopeai.com/api/v2/chat` through nginx).
5. Log sanity checks (`pericopeai-api`, `augustine-corpus-live`, nginx error log).

## 9) Rollback Rules

1. Define rollback target before deployment.
2. Rollback must use documented compose commands only.
3. Re-run release gates after rollback.
4. If data release failed, restore prior index/data snapshot and restart corpus/api.

## 10) Nginx Rules

1. `/api` must proxy to API host port (`127.0.0.1:18000` per compose lock).
2. Include long-read timeouts for chat workloads:
   - `proxy_connect_timeout`
   - `proxy_send_timeout`
   - `proxy_read_timeout`
3. Forward `Authorization` header.
4. Validate and reload with:
   - `nginx -t && systemctl reload nginx`

## 11) Documentation Rules

1. If a command changes, update the matching runbook in the same change.
2. If docs conflict, stop and resolve before deployment.
3. Keep one canonical source per topic:
   - deployment strategy: `docs/pericopeai-deployment.md`
   - environment contract: `docs/server-environments.md`
   - release execution: versioned runbooks
4. Additive updates are preferred; avoid destructive rewrites.

## 12) Commitment Scoping Rules

1. Do not execute against an umbrella roadmap label alone when it spans multiple phases, release types, or deploy surfaces.
2. Before work starts, split large items into named execution slices that can be completed, verified, and documented in one pass.
3. Prefer slice names such as:
   - `Phase A closeout`
   - `API contract`
   - `UI guardrail`
   - `rollback proof`
4. Status updates, release notes, and handoff summaries must reference the active slice, not only the parent umbrella.
5. If a commitment survives more than one verified iteration without closeout, stop and split it into smaller dated sub-commitments in the ledger before continuing.
6. Scope size is correct only when one slice has one primary objective, one verification bundle, and one clear stop condition.
7. When a semantic release reaches feature-complete locally, freeze its feature scope. Any remaining item must be labeled as deploy/access/publish pending, not treated as justification to keep adding features under the same release number.
8. Do not start forward roadmap work under a newer release while older semantic-release items remain unfinished. Carry-over work must be closed first.

## 13) Incident Rules

1. Stabilize first, optimize second.
2. Do not mix architecture changes into incident hotfixes.
3. Record:
   - symptom
   - immediate fix
   - root cause
   - prevention change (runbook/script gate)
4. Convert incident learnings into explicit checks, not tribal knowledge.

## 14) Definition of Discipline

Operational discipline exists when:

1. Deploy outcome is reproducible from docs.
2. No operator-specific shell state is required.
3. Rollback is deterministic and tested.
4. Data updates do not force unnecessary full reindex.
5. Promotion criteria are explicit and auditable.
