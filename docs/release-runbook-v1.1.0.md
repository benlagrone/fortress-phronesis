# PericopeAI Release Deployment Runbook v1.1.0

## Release Version

- **Semver release:** `v1.1.0`
- **Type:** Minor release (new features and deployment controls, no intended API contract break)

## Scope of v1.1.0

1. Persona access control by client profile (`client-access`):
   - Pericope profiles: `p-dev`, `p-qa`, `p-prod`
   - MDE profiles: `mde-dev`, `mde-qa`, `mde-prod`
2. Runtime filtering and enforcement of allowed authors in corpus routes.
3. Environment passthrough for profile-aware access in compose:
   - `ENVIRONMENT`
   - `ENV`
   - `CLIENT_ACCESS_PROFILE`
4. Author persona configuration expansion (middle-ground defaults across authors).

## Environments

1. **Local dev (mac):**
   - Compose project: `pericope-local`
   - API: `http://localhost:18000`
   - FE: `http://localhost:13080`
2. **QA server:**
   - Compose project: `fortress-phronesis` (same as prod contract)
   - Profile: `CLIENT_ACCESS_PROFILE=p-qa` (or `mde-qa` for MDE interface)
3. **Prod server:**
   - Compose project: `fortress-phronesis`
   - Profile: `CLIENT_ACCESS_PROFILE=p-prod` (or `mde-prod` for MDE interface)

## Pre-Release Checklist

1. Confirm repos are clean and on intended release commits:
   - `AugustineCorpus`
   - `AugustineService`
   - `AugustineFE`
   - `fortress-phronesis`
2. Confirm `AugustineCorpus/author_index.json` includes `client-access` for every author.
3. Confirm corpus/API env files have valid provider keys and DB values.
4. Confirm `AUTHOR_INDEX_MAP` can be generated from `author_index.json`.
5. Confirm texts are present in `AugustineCorpus/texts/*_texts`.

## Release Tagging (recommended)

Create the same version tag in each repo included in deployment.

```bash
git -C AugustineCorpus tag -a v1.1.0 -m "Release v1.1.0"
git -C AugustineService tag -a v1.1.0 -m "Release v1.1.0"
git -C AugustineFE tag -a v1.1.0 -m "Release v1.1.0"
git -C fortress-phronesis tag -a v1.1.0 -m "Release v1.1.0"
```

Push tags when ready:

```bash
git -C AugustineCorpus push origin v1.1.0
git -C AugustineService push origin v1.1.0
git -C AugustineFE push origin v1.1.0
git -C fortress-phronesis push origin v1.1.0
```

## Deployment Variables

Set these per environment before deploy:

1. `ENVIRONMENT` and `ENV`:
   - `dev` for local
   - `qa` for QA
   - `prd` for prod
2. `CLIENT_ACCESS_PROFILE`:
   - Pericope client: `p-dev`, `p-qa`, `p-prod`
   - MDE client: `mde-dev`, `mde-qa`, `mde-prod`
3. `CORPUS_VERSION`:
   - Set to `v1.1.0`

## Deploy Procedure

Run from `fortress-phronesis`:

```bash
cd /root/workspace/fortress-phronesis
```

1. Export release env:

```bash
export ENVIRONMENT=prd
export ENV=prd
export CLIENT_ACCESS_PROFILE=p-prod
export CORPUS_VERSION=v1.1.0
```

2. Build `AUTHOR_INDEX_MAP` from corpus index config:

```bash
export AUTHOR_INDEX_MAP="$(
python3 - <<'PY'
import json
p="/root/workspace/AugustineCorpus/author_index.json"
arr=json.load(open(p))
pairs=[]
for a in arr:
    slug=a.get("slug")
    idx=a.get("index_dir","").lstrip("./")
    if slug and idx:
        pairs.append(f"{slug}=/app/{idx}")
print(",".join(pairs))
PY
)"
```

3. Build and deploy stack:

```bash
docker compose -p fortress-phronesis -f docker-compose.pericope.yml up -d --build
docker compose -p fortress-phronesis -f docker-compose.pericope.yml ps
```

4. Ensure DB schema exists:

```bash
docker compose -p fortress-phronesis -f docker-compose.pericope.yml exec -T pericopeai-api python create_tables.py
```

5. Optional reindex (if texts or metadata changed):

```bash
docker compose -p fortress-phronesis -f docker-compose.pericope.yml --profile index run --rm pericopeai-indexer
docker compose -p fortress-phronesis -f docker-compose.pericope.yml restart augustine-corpus-live pericopeai-api
```

## Post-Deploy Verification

1. Health checks:

```bash
curl -fsS http://localhost:18000/api/healthz
curl -fsS http://localhost:13080 >/dev/null
docker compose -p fortress-phronesis -f docker-compose.pericope.yml exec -T augustine-corpus-live \
  python -c "import urllib.request; print(urllib.request.urlopen('http://localhost:8001/healthz', timeout=5).read().decode())"
```

2. Verify active profile in corpus container:

```bash
docker compose -p fortress-phronesis -f docker-compose.pericope.yml exec -T augustine-corpus-live \
  env | egrep '^(ENVIRONMENT|ENV|CLIENT_ACCESS_PROFILE|CORPUS_VERSION)='
```

3. Verify author visibility:

```bash
curl -s http://localhost:18000/api/v1/authors | python3 - <<'PY'
import sys, json
authors=json.load(sys.stdin)
slugs={a.get("slug") for a in authors}
print("authors:", len(authors))
print("alpha_present:", "alpha" in slugs)
PY
```

Expected in `p-prod` profile:
1. `alpha_present` is `False`.
2. Author count reflects prod-visible set.

## Author Quality Regression Test

```bash
mkdir -p /root/workspace/tests
python3 /root/workspace/fortress-phronesis/scripts/test-authors.py \
  --base-url http://localhost:18000 \
  --question "Summarize the main themes in 3-5 sentences and include citations." \
  --out /root/workspace/tests/author-chat-test-v1.1.0.jsonl
```

If failures occur, run text preflight:

```bash
python3 /root/workspace/fortress-phronesis/scripts/author-preflight.py \
  --author-index /root/workspace/AugustineCorpus/author_index.json \
  --texts-root /root/workspace/AugustineCorpus/texts \
  --format table
```

## Rollback

1. Reset env to previous release values (including `CORPUS_VERSION` and `CLIENT_ACCESS_PROFILE` if changed).
2. Checkout previous tagged commit in each repo.
3. Redeploy:

```bash
docker compose -p fortress-phronesis -f docker-compose.pericope.yml up -d --build
```

4. Re-run health checks and a limited author test sweep.

## Release Sign-Off

Approve release `v1.1.0` only if all are true:

1. API, FE, and corpus health checks pass.
2. Expected author visibility per profile is correct.
3. Full author regression run is acceptable.
4. No blocking errors in container logs.
