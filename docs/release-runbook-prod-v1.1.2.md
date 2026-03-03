# PericopeAI Prod Deployment Runbook v1.1.2

## Release Version

- Semver: `v1.1.2`
- Release date: `2026-02-27`
- Release type: Patch release

## Scope

1. Production deployment of `fortress-phronesis` stack (`mysql`, `augustine-corpus-live`, `pericopeai-api`, `pericopeai-frontend`).
2. DB schema bootstrap and validation, including DB-backed author catalog tables (`author_catalog`, `author_books`).
3. Author profile endpoint readiness (`/api/v1/authors/{author_slug}/profile`) via catalog sync from corpus.
4. Post-deploy readiness, regression checks, and rollback gates.

## Sacred Rules (Non-Negotiable)

1. `.env` files are the source of truth for runtime/build inputs.
2. Per-repo `.env` ownership is fixed:
   - `AugustineService/.env`
   - `AugustineCorpus/.env`
   - `AugustineFE/.env`
3. Do not create or rely on `fortress-phronesis/.env` for deployment behavior.
4. Do not use ad-hoc `export VAR=...` or inline `VAR=... docker compose ...` overrides during prod deploy.
5. Do not change architecture during release execution:
   - no live patching
   - no editing running containers
   - no changing compose project/network/service names
6. Frontend build-time `REACT_APP_*` values must come from the FE env file via compose `--env-file`.
7. Prod visibility rules are mandatory:
   - `ENV=prd` and/or `ENVIRONMENT=prd` in `AugustineService/.env` and `AugustineCorpus/.env`
   - `HIDE_LOCAL_ONLY=true` in `AugustineService/.env`

## Deployment Contract

1. Compose project: `fortress-phronesis`
2. Compose file: `docker-compose.pericope.yml`
3. Shared network: `fortress-phronesis-net`
4. Host ports:
   - MySQL `3307`
   - API `18000`
   - Frontend `13080`

## Preconditions

1. Repos are clean and at intended release commits:
   - `fortress-phronesis`
   - `AugustineService`
   - `AugustineCorpus`
   - `AugustineFE`
2. Production env files exist and are correct:
   - `../AugustineService/.env`
   - `../AugustineCorpus/.env`
   - `../AugustineFE/.env`
3. Corpus text assets are present on prod host (`../AugustineCorpus/texts/*_texts`).

## Step 0: Path Guard (Mandatory)

Run in the same shell used for deployment:

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
FE_COMPOSE="docker compose --env-file $FPR_ROOT/../AugustineFE/.env -p fortress-phronesis -f $FPR_ROOT/docker-compose.pericope.yml"

echo "FPR_ROOT=$FPR_ROOT"
echo "COMPOSE_FILE=$FPR_ROOT/docker-compose.pericope.yml"
echo "FE_ENV_FILE=$FPR_ROOT/../AugustineFE/.env"
```

Expected on prod:
- `FPR_ROOT=/root/workspace/fortress-phronesis`

## Step 1: Preflight

```bash
cd "$FPR_ROOT"

docker --version
docker compose version

bash scripts/verify-pericope-deploy-lock.sh

$COMPOSE config >/tmp/pericope-config-v1.1.2.yaml
grep -n '"18000:8080"\|"13080:80"\|"3307:3306"' /tmp/pericope-config-v1.1.2.yaml

grep -E '^(ENV|ENVIRONMENT|HIDE_LOCAL_ONLY)=' ../AugustineService/.env
grep -E '^(ENV|ENVIRONMENT)=' ../AugustineCorpus/.env
grep -E '^(CORPUS_API_URL|MYSQL_HOST|MYSQL_DB|MYSQL_USER)=' ../AugustineService/.env
```

## Step 2: Stop Old Stack Containers, Then Deploy Core Services

```bash
cd "$FPR_ROOT"

# End current stack containers before bringing up rebuilt containers.
$COMPOSE down --remove-orphans

$COMPOSE up -d --build mysql augustine-corpus-live pericopeai-api
$FE_COMPOSE up -d --build pericopeai-frontend
$COMPOSE ps
```

## Step 3: MySQL Readiness + Schema Bootstrap

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
SHOW TABLES LIKE '\''author_catalog'\'';
SHOW TABLES LIKE '\''author_books'\'';
"
'
```

## Step 4: Author Catalog Sync (v1.1.2 Gate)

```bash
cd "$FPR_ROOT"

$COMPOSE exec -T pericopeai-api python sync_author_catalog.py \
  --corpus-base http://augustine-corpus-live:8001 \
  --exclude-local-only
```

Verify profile endpoints:

```bash
curl -fsS http://localhost:18000/api/v1/authors/augustine/profile >/tmp/profile-augustine-v1.1.2.json
curl -fsS http://localhost:18000/api/v1/authors/freud/profile >/tmp/profile-freud-v1.1.2.json
```

## Step 5: Optional Indexing

Use targeted indexing if only specific authors changed; full indexing otherwise.

```bash
cd "$FPR_ROOT"

$COMPOSE --profile index run --rm pericopeai-indexer \
  python preprocess_and_index.py

$COMPOSE restart augustine-corpus-live pericopeai-api
```

## Step 6: Readiness Gates

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
  echo "waiting for authors..."
  sleep 2
done

until curl -fsS http://localhost:18000/api/v1/authors/freud/profile >/dev/null; do
  echo "waiting for profile endpoint..."
  sleep 2
done

until curl -fsS http://localhost:13080 >/dev/null; do
  echo "waiting for frontend..."
  sleep 2
done
```

## Step 7: Regression Tests

Smoke:

```bash
cd "$FPR_ROOT"
mkdir -p tests

python3 scripts/test-authors.py \
  --base-url http://localhost:18000 \
  --question "Summarize the main themes in 3-5 sentences and include citations." \
  --exclude-local-only \
  --authors augustine,freud \
  --timeout 240 \
  --out tests/author-chat-smoke-v1.1.2.jsonl
```

Full sweep:

```bash
cd "$FPR_ROOT"
python3 scripts/test-authors.py \
  --base-url http://localhost:18000 \
  --question "Summarize the main themes in 3-5 sentences and include citations." \
  --exclude-local-only \
  --timeout 240 \
  --out tests/author-chat-test-v1.1.2.jsonl
```

## Step 8: Rollback

1. Checkout previous release commits/tags for all four repos.
2. Restore prior text assets if release included corpus updates.
3. Rebuild stack:

```bash
cd "$FPR_ROOT"
$COMPOSE up -d --build
```

4. Re-run readiness gates and smoke tests.

## Release Sign-Off

Approve `v1.1.2` only if all are true:

1. Readiness gates passed.
2. DB tables exist (`users`, `messages`, `citations`, `author_catalog`, `author_books`).
3. `sync_author_catalog.py` completed without errors.
4. Author profile endpoints return `200` for production-visible test authors.
5. Smoke and full regression passed.
6. No blocking logs in:

```bash
docker compose -p fortress-phronesis -f docker-compose.pericope.yml logs --tail=200 pericopeai-api augustine-corpus-live mysql
```
