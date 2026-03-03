# PericopeAI Dev Server Container Deployment Runbook

This runbook deploys the PericopeAI container stack to the dev server using the locked compose contract.

## Deployment Contract

1. Compose project name: `fortress-phronesis`
2. Compose file: `docker-compose.pericope.yml`
3. Network name: `fortress-phronesis-net`
4. Host ports:
   - MySQL: `3307`
   - API: `18000`
   - Frontend: `13080`
5. Runtime environment values come from repo `.env` files, not ad-hoc shell exports.

## Non-Negotiable Guardrails

1. Do not change host ports in compose or via overrides.
2. Do not use ad-hoc shell env injection for deploy commands (`export ...`, `VAR=... docker compose ...`).
3. Do not change compose project name, compose file path, or network name.
4. Always run `bash scripts/verify-pericope-deploy-lock.sh` before deploy.
5. Frontend build-time vars must come from `../AugustineFE/.env` via `--env-file` only.

Allowed deployment command forms:

```bash
docker compose -p fortress-phronesis -f docker-compose.pericope.yml up -d --build mysql augustine-corpus-live pericopeai-api
docker compose --env-file ../AugustineFE/.env -p fortress-phronesis -f docker-compose.pericope.yml up -d --build pericopeai-frontend
docker compose -p fortress-phronesis -f docker-compose.pericope.yml ps
docker compose -p fortress-phronesis -f docker-compose.pericope.yml logs --tail=200 pericopeai-api
docker compose -p fortress-phronesis -f docker-compose.pericope.yml restart pericopeai-api pericopeai-frontend
```

## Target Dev Host

- Host: `fortress-phronesis` (`192.168.86.23`)
- Workspace root: `/home/master-benjamin/Projects/pericopeai.com`
- Stack root: `/home/master-benjamin/Projects/pericopeai.com/fortress-phronesis`

## Step 0: SSH and Path Guard

From your local machine:

```bash
ssh master-benjamin@192.168.86.23
```

On the dev host:

```bash
if [ -f ~/Projects/pericopeai.com/fortress-phronesis/docker-compose.pericope.yml ]; then
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

Expected:
- `FPR_ROOT=/home/master-benjamin/Projects/pericopeai.com/fortress-phronesis`

## Step 1: Preflight

```bash
cd "$FPR_ROOT"

docker --version
docker compose version

# Ensure deployment contract in compose file is intact.
bash scripts/verify-pericope-deploy-lock.sh

# Validate compose resolution.
$COMPOSE config >/tmp/pericope-dev-config.yaml
```

Confirm required env files exist:

```bash
ls -l ../AugustineCorpus/.env ../AugustineService/.env ../AugustineFE/.env
```

Ensure shared network exists:

```bash
docker network create fortress-phronesis-net 2>/dev/null || true
```

## Step 2: Update Code (Optional but Typical)

```bash
git -C ../AugustineCorpus pull --ff-only
git -C ../AugustineService pull --ff-only
git -C ../AugustineFE pull --ff-only
git -C "$FPR_ROOT" pull --ff-only
```

## Step 3: Deploy Containers

Deploy backend services first, then frontend:

```bash
cd "$FPR_ROOT"

$COMPOSE up -d --build mysql augustine-corpus-live pericopeai-api
$FE_COMPOSE up -d --build pericopeai-frontend
$COMPOSE ps
```

## Step 4: Bootstrap/Validate DB Tables

```bash
cd "$FPR_ROOT"

$COMPOSE exec -T mysql sh -lc '
until mysqladmin ping -h127.0.0.1 -uroot -p"$MYSQL_ROOT_PASSWORD" --silent; do
  echo "waiting for mysql..."
  sleep 2
done
echo "mysql ready"
'

$COMPOSE exec -T pericopeai-api python create_tables.py

$COMPOSE exec -T mysql sh -lc '
DB="${MYSQL_DATABASE:-augustine_chat}"
mysql -h127.0.0.1 -uroot -p"$MYSQL_ROOT_PASSWORD" -D "$DB" -e "
SHOW TABLES LIKE '\''users'\'';
SHOW TABLES LIKE '\''messages'\'';
SHOW TABLES LIKE '\''citations'\'';
"
'
```

## Step 5: Reindex Corpus (Only If Texts/Metadata Changed)

Targeted author reindex:

```bash
cd "$FPR_ROOT"

$COMPOSE --profile index run --rm pericopeai-indexer \
  python preprocess_and_index.py \
  --author solomon_expanded \
  --texts-root /app/texts \
  --index-dir /app/indexes/solomon_expanded
```

Full reindex:

```bash
cd "$FPR_ROOT"
$COMPOSE --profile index run --rm pericopeai-indexer python preprocess_and_index.py
```

After either reindex:

```bash
$COMPOSE restart augustine-corpus-live pericopeai-api
```

## Step 6: Smoke Checks

```bash
cd "$FPR_ROOT"

curl -fsS http://localhost:18000/api/healthz
curl -fsS http://localhost:18000/api/v1/authors >/tmp/dev-authors.json
curl -fsS http://localhost:13080 >/dev/null

$COMPOSE exec -T pericopeai-api \
  python -c "import urllib.request; urllib.request.urlopen('http://augustine-corpus-live:8001/healthz', timeout=5).read(); print('corpus ok')"

python3 scripts/test-authors.py \
  --base-url http://localhost:18000 \
  --question "Summarize the main themes in 3-5 sentences and include citations." \
  --authors augustine,solomon_expanded \
  --timeout 240 \
  --out tests/author-chat-dev-smoke.jsonl
```

## Step 7: Logs and Troubleshooting

```bash
cd "$FPR_ROOT"

$COMPOSE ps
$COMPOSE logs --tail=200 pericopeai-api
$COMPOSE logs --tail=200 augustine-corpus-live
$COMPOSE logs --tail=200 pericopeai-frontend
```

If frontend is unexpectedly published on `3000` instead of `13080`:

```bash
cd "$FPR_ROOT"

# Confirm effective mapping from compose resolution.
$COMPOSE config | grep -nE '13080:80|3000:80'

# Enforce deployment contract mapping.
sed -i 's/"3000:80"/"13080:80"/g' docker-compose.pericope.yml

# Recreate frontend with locked mapping.
$FE_COMPOSE up -d --build --force-recreate --no-deps pericopeai-frontend

# Verify final runtime port.
docker ps --filter name=fortress-phronesis-pericopeai-frontend-1 \
  --format 'table {{.Names}}\t{{.Ports}}\t{{.Status}}'
```

If port `3307` is already in use:

```bash
docker ps --format 'table {{.Names}}\t{{.Ports}}'
docker stop pericope-local-mysql-1 2>/dev/null || true
```

Then redeploy MySQL:

```bash
cd "$FPR_ROOT"
$COMPOSE up -d --build mysql
```

## Step 8: Stop or Roll Back

Stop stack but keep data:

```bash
cd "$FPR_ROOT"
$COMPOSE stop
```

Rebuild and redeploy previous known-good commits:

```bash
git -C ../AugustineCorpus checkout <known-good-commit-or-tag>
git -C ../AugustineService checkout <known-good-commit-or-tag>
git -C ../AugustineFE checkout <known-good-commit-or-tag>
git -C "$FPR_ROOT" checkout <known-good-commit-or-tag>

cd "$FPR_ROOT"
$COMPOSE up -d --build
```

## Scope Guard

This runbook controls only the PericopeAI dev stack (`fortress-phronesis` compose project). It does not operate on unrelated projects like `data-fabric-table-v2`.
