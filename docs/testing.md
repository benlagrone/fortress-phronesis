# PericopeAI Author Test Runner

This doc covers the author sweep test script that asks every author a question and records response metrics.

## Script
- `fortress-phronesis/scripts/test-authors.py`

## What it records
- `status`: HTTP status from `/api/v2/chat`
- `elapsed_ms`: request duration in milliseconds
- `response_bytes`: raw response size
- `answer_chars` / `answer_words`: response length
- `citations`: count of citation entries returned
- `books`: count of referenced books returned
- `metadata`: count of metadata entries returned
- `position_min` / `position_max`: min/max of `metadata.position` (useful to spot file-level indexing when all positions are `1`)
- `error`: request or parse error, if any
- `pass`: boolean based on thresholds below
- `fail_reasons`: list of failed checks

## Prereqs
- Python 3 available on the host running the script.
- Pericope API reachable at the base URL you pass in.

## Usage
Default (tests all authors, writes JSONL):
```bash
fortress-phronesis/scripts/test-authors.py \
  --base-url http://localhost:18000 \
  --question "test" \
  --out /tmp/author-chat-test.jsonl
```

Lock-in smoke (recommended after every deploy):
```bash
python3 fortress-phronesis/scripts/test-authors.py \
  --base-url http://localhost:18000 \
  --question "Summarize the main themes in 3-5 sentences and include citations." \
  --exclude-local-only \
  --authors augustine,marcus_aurelius \
  --timeout 240 \
  --out tests/author-chat-lockin.jsonl
```

Visible terminal smoke (recommended default):
```bash
cd fortress-phronesis
python3 scripts/smoke-tests.py \
  --base-url http://localhost:18000 \
  --out tests/author-chat-smoke-visible.jsonl
```

This prints live progress plus a final PASS/FAIL summary table in terminal.

Payment fixture smoke:
```bash
cd fortress-phronesis
python3 scripts/verify-pericope-payment-smoke.py \
  --api-base-url http://127.0.0.1:18000/api \
  --user-id dummy-paid-reader \
  --initial-roles default-roles-pericope \
  --promoted-roles reader
```

Prereqs for the payment smoke:
- `AugustineService` is running with `AUTH_ENFORCED=false`, `DEV_FAKE_AUTH=true`, and `PERICOPE_BILLING_PROVIDER=fixture`.
- The smoke uses `X-Dev-Auth-*` headers to drive the dummy account flow without a live Keycloak browser login.
- Browser-side billing regression remains covered by `AugustineFE` `src/App.test.js`.

Mobile paid-access checks:
```bash
cd pericopeai-mobile-app
npm run typecheck
npm run check:layout
npm run check:billing
```

The backend auth suite separately verifies that `/api/v2/mobile/chat` rejects
an authenticated account without `reader` and accepts a `reader` token. The
mobile helper check covers all four billing access states and keeps chat
disabled until the status is `paid_active`.

Browser payment E2E:
```bash
cd fortress-phronesis
PERICOPE_PYTHON_BIN=/tmp/pericopeai-test-venv/bin/python \
python3 scripts/verify-pericope-payment-browser-e2e.py
```

What the browser harness covers:
- starts a local fixture API with `DEV_FAKE_AUTH=true`
- starts `AugustineFE` with dummy local auth enabled
- opens `/pricing` in a real browser via Playwright CLI
- starts the Reader checkout
- completes the dummy payment on `/billing/success`
- creates the customer portal link
- promotes the local dummy runtime role to `reader`
- verifies the paid state on `/user/profile/home`

Artifacts land under `fortress-phronesis/output/playwright/pericope-payment-e2e/`.

Cross-reference API smoke (v1.3.0 bootstrap):
```bash
cd fortress-phronesis
python3 scripts/smoke-crossrefs.py \
  --base-url http://localhost:18000 \
  --out tests/crossref-smoke-visible.json
```

Optional scoped author check:
```bash
python3 scripts/smoke-crossrefs.py \
  --base-url http://localhost:18000 \
  --author moses
```

Note: for bootstrap crossref validation, use an author slug that currently has mapped crossref entries (for example `moses`).

Dev server example:
```bash
fortress-phronesis/scripts/test-authors.py \
  --base-url http://192.168.86.23:18000 \
  --question "test" \
  --out /tmp/author-chat-test-dev.jsonl
```

CSV output:
```bash
fortress-phronesis/scripts/test-authors.py \
  --base-url http://192.168.86.23:18000 \
  --format csv \
  --out /tmp/author-chat-test-dev.csv
```

## Filters and limits
- Test only specific authors:
  ```bash
  fortress-phronesis/scripts/test-authors.py --authors alpha,amos
  ```
- Limit the run:
  ```bash
  fortress-phronesis/scripts/test-authors.py --limit 10
  ```
- Exclude `local_only` authors:
  ```bash
  fortress-phronesis/scripts/test-authors.py --exclude-local-only
  ```

## Preflight text check
Use this to confirm `.txt` input presence for each author (or only failed authors).

All authors:
```bash
fortress-phronesis/scripts/author-preflight.py
```

Only failed authors from a test run:
```bash
fortress-phronesis/scripts/author-preflight.py \
  --results tests/author-chat-test.jsonl
```

JSONL output:
```bash
fortress-phronesis/scripts/author-preflight.py \
  --format jsonl \
  --out tests/author-text-preflight.jsonl
```

## Pass/Fail thresholds (optional)
Defaults are enabled; set any to `0` to disable.
- `--min-answer-chars` (default: 200)
- `--min-citations` (default: 1)
- `--min-books` (default: 1)
- `--min-metadata` (default: 1)
- `--min-position-max` (default: 2)
- `--max-elapsed-ms` (default: 0 = disabled)

Example strict run:
```bash
fortress-phronesis/scripts/test-authors.py \
  --base-url http://localhost:8080 \
  --min-answer-chars 400 \
  --min-position-max 10 \
  --out /tmp/author-chat-test.jsonl
```

Notes:
- Non-zero exit code when any author fails a threshold.
- Failures are printed at the end with reasons.

## Interpreting results
- `position_min` and `position_max` should be high for paragraph-level indexing.
  - If you see only `1`, the index is likely file-level (title-page issue).
- Low `answer_chars` with `citations=0` usually indicates failed retrieval.
- Non-200 `status` or a populated `error` indicates a request failure.
