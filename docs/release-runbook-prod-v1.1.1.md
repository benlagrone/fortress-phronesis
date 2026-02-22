# PericopeAI Prod Deployment Runbook v1.1.1

## Release Version

- Semver: `v1.1.1`
- Release date: `2026-02-18`
- Release type: Patch release

## Scope

1. Production deployment of `fortress-phronesis` stack (`mysql`, `augustine-corpus-live`, `pericopeai-api`, `pericopeai-frontend`).
2. DB schema bootstrap and validation (`users`, `messages`, `citations`).
3. Corpus text/index validation including `marcus_aurelius`.
4. Post-deploy regression and rollback gates.

## Sacred Rules (Non-Negotiable)

1. `.env` files are the source of truth for runtime and build inputs.
2. Per-repo `.env` ownership is fixed:
   - `AugustineService/.env`
   - `AugustineCorpus/.env`
   - `AugustineFE/.env`
3. Do not create or rely on a top-level `fortress-phronesis/.env` for deployment behavior.
4. Do not use ad-hoc `export VAR=...` or inline `VAR=... docker compose ...` overrides during prod deploy.
5. Do not change deployment architecture during release execution:
   - no live patching containers
   - no editing running containers
   - no changing compose project/network/service names
6. Frontend `REACT_APP_*` values are build-time inputs. They must come from compose interpolation using the intended env file, not manual shell injection.
7. For frontend builds, pass the env file explicitly:
   - `docker compose --env-file /root/workspace/AugustineFE/.env -p fortress-phronesis -f /root/workspace/fortress-phronesis/docker-compose.pericope.yml up -d --build pericopeai-frontend`
8. Prod visibility rules are mandatory:
   - `ENV=prd` and/or `ENVIRONMENT=prd` in `AugustineService/.env` and `AugustineCorpus/.env`
   - `HIDE_LOCAL_ONLY=true` in `AugustineService/.env`
9. If any guard fails (path mismatch, env mismatch, `502` on `/api/v1/authors`), stop and fix before proceeding.

## Deployment Contract

1. Follow the Sacred Rules above without exception.
2. Runtime values must come from stack `.env` files:
   - `AugustineService/.env`
   - `AugustineCorpus/.env`
3. Compose project must remain `fortress-phronesis`.
4. Shared network must remain `fortress-phronesis-net`.
5. This runbook is for update deployments on an already provisioned server (not first-time bootstrap).

## Preconditions

1. Repos are clean and on intended release commits:
   - `fortress-phronesis`
   - `AugustineService`
   - `AugustineCorpus`
   - `AugustineFE`
2. `AugustineService/.env` and `AugustineCorpus/.env` are present on prod and set for production:
   - `ENVIRONMENT=prd`
   - `ENV=prd`
3. Corpus text assets are present on prod host under `AugustineCorpus/texts/*_texts` (these are git-ignored and must be synced/uploaded separately).
4. `docker-compose.pericope.yml` in `fortress-phronesis` includes `marcus_aurelius` mounts and index volume.

## Step 0: Path Guard (Mandatory)

Do this first in the same shell you will use for deployment:

```bash
if [ -f ~/workspace/fortress-phronesis/docker-compose.pericope.yml ]; then
  FPR_ROOT=~/workspace/fortress-phronesis
elif [ -f ~/Projects/pericopeai.com/fortress-phronesis/docker-compose.pericope.yml ]; then
  FPR_ROOT=~/Projects/pericopeai.com/fortress-phronesis
else
  FPR_ROOT="$(dirname "$(find ~ -maxdepth 5 -name docker-compose.pericope.yml 2>/dev/null | head -n1)")"
fi

FPR_ROOT="$(cd "$FPR_ROOT" && pwd)"
COMPOSE="docker compose -p fortress-phronesis -f $FPR_ROOT/docker-compose.pericope.yml"

echo "FPR_ROOT=$FPR_ROOT"
echo "COMPOSE_FILE=$FPR_ROOT/docker-compose.pericope.yml"
```

Expected on prod:
- `FPR_ROOT=/root/workspace/fortress-phronesis`
- `COMPOSE_FILE=/root/workspace/fortress-phronesis/docker-compose.pericope.yml`

## Step 1: Preflight

Run on prod host:

```bash
cd "$FPR_ROOT"

docker --version
docker compose version

$COMPOSE config >/tmp/pericope-config-v1.1.1.yaml
grep -n "marcus_aurelius_texts\\|corpus_marcus_aurelius_index" /tmp/pericope-config-v1.1.1.yaml

ls -lh ../AugustineCorpus/texts/marcus_aurelius_texts/*.txt
```

## Step 2: Deploy Core Services

```bash
cd "$FPR_ROOT"

$COMPOSE up -d --build mysql augustine-corpus-live pericopeai-api pericopeai-frontend
$COMPOSE ps
```

## Step 3: MySQL Readiness and Schema Bootstrap

```bash
cd "$FPR_ROOT"

$COMPOSE exec -T mysql sh -lc '
until mysqladmin ping -h127.0.0.1 -uroot -p"$MYSQL_ROOT_PASSWORD" --silent; do
  echo "waiting for mysql..."
  sleep 2
done
echo "mysql ready"
'

$COMPOSE exec -T pericopeai-api sh -lc '
for i in $(seq 1 20); do
  echo "create_tables attempt $i"
  python create_tables.py && exit 0
  sleep 3
done
exit 1
'

$COMPOSE exec -T mysql sh -lc '
DB="${MYSQL_DATABASE:-augustine_chat}"
mysql -h127.0.0.1 -uroot -p"$MYSQL_ROOT_PASSWORD" -D "$DB" -e "
SHOW TABLES LIKE '\''users'\'';
SHOW TABLES LIKE '\''messages'\'';
SHOW TABLES LIKE '\''citations'\'';
"
'
```

## Step 4: Indexing

Use targeted indexing when only one author changed; full indexing otherwise.

Targeted (`marcus_aurelius`):

```bash
cd "$FPR_ROOT"

$COMPOSE --profile index run --rm pericopeai-indexer \
  python preprocess_and_index.py \
  --author marcus_aurelius \
  --texts-root /app/texts \
  --index-dir /app/indexes/marcus_aurelius
```

Full:

```bash
cd "$FPR_ROOT"

$COMPOSE --profile index run --rm pericopeai-indexer \
  python preprocess_and_index.py
```

Restart corpus and API after indexing:

```bash
$COMPOSE restart augustine-corpus-live pericopeai-api
```

## Step 5: Readiness Gates

```bash
cd "$FPR_ROOT"

until $COMPOSE exec -T pericopeai-api \
  python -c "import urllib.request; urllib.request.urlopen('http://augustine-corpus-live:8001/healthz', timeout=5).read()" >/dev/null 2>&1; do
  echo "waiting for corpus..."
  sleep 2
done

until curl -fsS http://localhost:18000/api/healthz >/dev/null; do
  echo "waiting for api..."
  sleep 2
done

until curl -fsS http://localhost:18000/api/v1/authors >/dev/null; do
  echo "waiting for authors endpoint..."
  sleep 2
done
```

## Step 6: Regression Tests

Smoke:

```bash
cd "$FPR_ROOT"
mkdir -p tests

python3 scripts/test-authors.py \
  --base-url http://localhost:18000 \
  --question "Summarize the main themes in 3-5 sentences and include citations." \
  --exclude-local-only \
  --authors augustine,marcus_aurelius \
  --timeout 240 \
  --out tests/author-chat-smoke-v1.1.1.jsonl
```

Full sweep:

```bash
cd "$FPR_ROOT"
python3 scripts/test-authors.py \
  --base-url http://localhost:18000 \
  --question "Summarize the main themes in 3-5 sentences and include citations." \
  --exclude-local-only \
  --timeout 240 \
  --out tests/author-chat-test-v1.1.1.jsonl
```

Pass gate:

1. `ok` equals expected author count.
2. No `HTTPError 500`.
3. No systemic `citations<1` failures.

## Step 7: Rollback

1. Checkout previous release tags/commits for all four repos.
2. Restore prior text assets if this release included corpus text updates.
3. Rebuild and restart stack:

```bash
cd "$FPR_ROOT"
$COMPOSE up -d --build
```

4. Re-run Step 5 readiness gates and a smoke test.

## Release Sign-Off

Approve `v1.1.1` only if all are true:

1. Readiness gates passed.
2. DB tables exist (`users`, `messages`, `citations`).
3. Smoke and full regression passed.
4. No blocking errors in:

```bash
docker compose -p fortress-phronesis -f docker-compose.pericope.yml logs --tail=200 pericopeai-api augustine-corpus-live mysql
```
