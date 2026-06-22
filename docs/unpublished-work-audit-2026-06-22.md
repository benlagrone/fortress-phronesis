# Unpublished Work Audit — 2026-06-22

Purpose: inventory unfinished, uncommitted, unmerged, and unpublished work after
the Ask Proverbs Pericope commits and mobile voice planning docs were pushed.

## Summary

| Repo | Branch state | Dirty state | Classification |
| --- | --- | --- | --- |
| `fortress-phronesis` | Local checkout: `main...origin/main [ahead 19, behind 151]` | Dirty, many tracked and untracked files | Divergent and unsafe to merge blindly |
| `AugustineCorpus` | `master...origin/master` | Clean | Published |
| `AugustineService` | `master...origin/master` | Clean | Published |
| `AugustineFE` | `master...origin/master` | Clean | Published |
| `Solomonic_Seals` | `main...origin/main [ahead 1]` | Dirty code/docs/tests plus untracked files | Unpublished local commit plus uncommitted clock/router work |
| `Model_Discernment_Engine` | `main...origin/main` | Dirty code/config/docs/generated reports | Uncommitted MDE detector/report work |
| `pericopeai-mobile-app` | `main`, no upstream configured | Dirty app/packages/services/UI | Unpublished repo state; no remote tracking branch |
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

Validation before push:

- `AugustineCorpus`: `python3 -m pytest` -> 34 passed
- `AugustineService`: `python3 -m pytest` -> 72 passed, 19 skipped
- `AugustineFE`: `npm test -- --watchAll=false` -> 35 passed

## Remaining Unpublished Commit

| Repo | Commit | Subject |
| --- | --- | --- |
| `Solomonic_Seals` | `f7e6828` | Expose clock guided prompts API |

## Fortress Phronesis Local Checkout

The active local checkout remains divergent and dirty:

- `main...origin/main [ahead 19, behind 151]`
- tracked and untracked docs, workflow, deploy, and script changes are mixed

Do not push, pull, merge, or rebase that checkout directly. Continue using clean
worktrees from `origin/main` for intentional publishable slices until the local
divergent history is either reconciled, archived, or retired by explicit
operator decision.

## Solomonic Seals Dirty Worktree

Tracked modified areas include:

- clock/pericope contract docs
- mobile app roadmap docs
- clock frontend JavaScript/CSS
- clock drawer and VibeVoice frontend contract tests
- generated clock data

Untracked areas include:

- local router/deploy files
- deployment promotion runbook and smoke script
- Pericope launch contract test and frontend helper
- drawer UX mockup
- Playwright console log

Classification: clock/pericope bridge, local-router/deployment-promotion,
drawer UX, generated clock data, and launch-contract work are mixed. Split into
intentional publishable commits before pushing.

## Model Discernment Engine Dirty Worktree

Tracked modified areas include:

- detector/config work
- report rendering and scripture-only logic
- docs/marketing copy
- generated public reports

Untracked areas include:

- candidate queue source and tests
- candidate grounding/promotion scripts
- pending candidate runs and generated live report output

Classification: candidate-detector queue/promotion work plus generated report
outputs. Source changes and generated artifacts must be separated before
publication.

## Pericope Mobile App Dirty Worktree

Branch: `main`; no upstream tracking branch configured.

Tracked modified files include:

- `App.tsx`
- `README.md`
- `app.json`
- `package-lock.json`
- `package.json`
- `src/api/client.ts`
- `src/api/types.ts`

Untracked directories include:

- `scripts/`
- `src/services/`
- `src/ui/`

Classification: mobile app implementation work with no configured publication
target. Choose a remote/upstream before calling this work merged or published.

## Required Closeout

1. Publish this audit and roadmap rectification from the clean Fortress worktree.
2. Split and publish or intentionally supersede `Solomonic_Seals` work.
3. Split MDE source changes from generated reports before any MDE publication.
4. Configure a remote/upstream for `pericopeai-mobile-app` or explicitly keep it
   local-only.
5. Only after the gate is clear, start `v1.4.0` pricing/subscriptions and
   `v1.4.0-ops` reliability work.
