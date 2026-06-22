# Unpublished Work Audit — 2026-06-22

Purpose: inventory unfinished, uncommitted, unmerged, and unpublished work after
the Ask Proverbs, Solomonic, MDE, and mobile cleanup pass.

## Summary

| Repo | Branch state | Dirty state | Classification |
| --- | --- | --- | --- |
| `fortress-phronesis` | `main...origin/main` | Clean | Divergent local state quarantined |
| `AugustineCorpus` | `master...origin/master` | Clean | Published |
| `AugustineService` | `master...origin/master` | Clean | Published |
| `AugustineFE` | `master...origin/master` | Clean | Published |
| `Solomonic_Seals` | `main...origin/main` | Clean | Published |
| `Model_Discernment_Engine` | `main...origin/main` | Clean | Published |
| `pericopeai-mobile-app` | `main`, no upstream configured | Clean | Local commit exists; no remote tracking branch |
| `AugustineCorpusGateway` | `main...origin/main` | Clean | No unpublished work detected |
| `pericopeai-assets` | `main...origin/main` | Clean | No unpublished work detected |
| `latin-rag-translator` | `main...origin/main` | Clean | No unpublished work detected |

## Published Since Prior Audit

| Repo | Commit | Subject |
| --- | --- | --- |
| `AugustineCorpus` | `934c05a` | Route corpus generation through Ollama |
| `AugustineService` | `e359072` | Add Ask Proverbs API contract |
| `AugustineFE` | `6bae97c` | Add Ask Proverbs frontend |
| `AugustineFE` | `a818a0b` | Document mobile voice roadmap scope |
| `Solomonic_Seals` | `f7e6828` | Expose clock guided prompts API |
| `Solomonic_Seals` | `7773cfa` | Add clock mobile readiness and launch contracts |
| `Solomonic_Seals` | `4a5515d` | Load clock dataset from API with fallback |
| `Solomonic_Seals` | `fc7dad8` | Guard API-first clock dataset loading |
| `Model_Discernment_Engine` | `38c4903` | Add candidate grounding promotion workflow |
| `Model_Discernment_Engine` | `1957bca` | Publish refreshed detector reports |

Validation before push:

- `AugustineCorpus`: `python3 -m pytest` -> 34 passed
- `AugustineService`: `python3 -m pytest` -> 72 passed, 19 skipped
- `AugustineFE`: `npm test -- --watchAll=false` -> 35 passed
- `Solomonic_Seals`: all `tests/*.mjs` via Node -> passed
- `Solomonic_Seals`: `python3 -m pytest` -> 22 passed
- `Solomonic_Seals`: `python3 src/validate_json.py data/solomonic_clock_full.json` -> passed
- `Model_Discernment_Engine`: `python3 -m pytest` -> 15 passed

## Local-Only Commit

| Repo | Commit | Subject | Blocker |
| --- | --- | --- | --- |
| `pericopeai-mobile-app` | `b357260` | Add mobile auth voice layout skeleton | No remote repository exists and no upstream is configured |

Validation:

- `pericopeai-mobile-app`: `npm run typecheck` -> passed
- `pericopeai-mobile-app`: `npm run check:layout` -> passed

## Fortress Phronesis Local Checkout

The active local checkout has been reconciled to the published branch:

- active branch: `main`
- upstream: `origin/main`
- status: clean

The prior divergent state was preserved, not discarded:

- branch: `quarantine/fortress-local-main-20260622`
- backup branch: `quarantine/fortress-main-20260622`
- stash: `stash@{0}: On main: quarantine fortress dirty worktree 2026-06-22`

Use those only for intentional recovery/cherry-pick work. Do not merge the
quarantine branch blindly back into `main`.

## Solomonic Seals Closeout

The Solomonic work was split into tested publishable state and pushed to
`origin/main`.

- `f7e6828` publishes the clock guided prompts API.
- `7773cfa` publishes mobile readiness, drawer UX, Pericope launch contracts,
  local-router/deployment-promotion docs, and contract tests.
- `4a5515d` publishes `/api/clock` dataset loading with bundled JSON fallback.
- `fc7dad8` publishes the contract test guard for API-first dataset loading.
- Runtime scratch logs under `.playwright-cli/` are ignored and were not
  committed.

## Model Discernment Engine Closeout

The MDE work was split into source and generated-output commits and pushed to
`origin/main`.

- `38c4903` publishes candidate queue grounding/promotion source, docs, config,
  and tests.
- `1957bca` publishes refreshed public report artifacts and run outputs.

## Pericope Mobile App Local Commit

Branch: `main`; no upstream tracking branch configured.

The mobile app work is committed locally as `b357260 Add mobile auth voice
layout skeleton` and the worktree is clean. It is not published because no
remote exists for the repository. A probe for
`https://github.com/benlagrone/pericopeai-mobile-app.git` returned
`Repository not found`, and the GitHub CLI is not installed in this environment.

## Required Closeout

1. Configure a remote/upstream for `pericopeai-mobile-app` or explicitly keep it
   local-only.
2. Start `v1.4.0` pricing/subscriptions and
   `v1.4.0-ops` reliability work.
