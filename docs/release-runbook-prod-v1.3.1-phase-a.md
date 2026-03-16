# PericopeAI Prod Deployment Runbook v1.3.1 Phase A

## Release Version

- Semver slice: `v1.3.1 Phase A`
- Release date: `2026-03-16`
- Release type: additive API/schema release

## Scope

1. Production deployment of the `pericopeai-api` code release on the shared `fortress-phronesis` stack.
2. DB schema bootstrap for:
   - `service_catalog`
   - `service_versions`
   - `lead_intakes`
3. Validation of registry-backed service endpoints:
   - `GET /api/v1/services`
   - `GET /api/v1/services/{service_id}/metadata`
   - `GET /api/v1/services/{service_id}/version`
4. Preserve existing `/api/v2/chat` behavior and current frontend/corpus/clock runtime behavior.

## Out of Scope

1. Full service promotion/rollback controls.
2. MDE promotion-gate enforcement.
3. Warehouse/audit tables.
4. Frontend redesign or corpus reindex beyond what is already live.

## Preconditions

1. Repos are clean and at intended release commits:
   - `fortress-phronesis`
   - `AugustineService`
2. Runtime env files exist:
   - `../AugustineService/.env`
   - `../AugustineCorpus/.env`
   - `../AugustineFE/.env`
   - `../Solomonic_Seals/.env` when guided prompts are enabled
3. If intake is intended to be live, `AugustineService/.env` defines the required intake allow-list and follow-up values.

## Step 0: Path Guard

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
CLOCK_COMPOSE="$COMPOSE"
if [ -f "$FPR_ROOT/../Solomonic_Seals/.env" ]; then
  CLOCK_COMPOSE="docker compose --env-file $FPR_ROOT/../Solomonic_Seals/.env -p fortress-phronesis -f $FPR_ROOT/docker-compose.pericope.yml"
fi

echo "FPR_ROOT=$FPR_ROOT"
echo "COMPOSE_FILE=$FPR_ROOT/docker-compose.pericope.yml"
echo "FE_ENV_FILE=$FPR_ROOT/../AugustineFE/.env"
echo "CLOCK_ENV_FILE=$FPR_ROOT/../Solomonic_Seals/.env"
```

Expected on prod:
- `FPR_ROOT=/root/workspace/fortress-phronesis`

## Step 1: Preflight

```bash
cd "$FPR_ROOT"

docker --version
docker compose version

bash scripts/verify-pericope-deploy-lock.sh

$CLOCK_COMPOSE config >/tmp/pericope-config-v1.3.1-phase-a.yaml
grep -n '"18000:8080"\|"13080:80"\|"8086:8080"\|"3307:3306"' /tmp/pericope-config-v1.3.1-phase-a.yaml

cd ../AugustineService
git status --short
git log --oneline -1
```

## Step 2: Deploy API Release

```bash
cd "$FPR_ROOT"

$COMPOSE up -d --build pericopeai-api
$COMPOSE ps pericopeai-api
```

## Step 3: Schema Bootstrap

```bash
cd "$FPR_ROOT"

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
SHOW TABLES LIKE '\''service_catalog'\'';
SHOW TABLES LIKE '\''service_versions'\'';
SHOW TABLES LIKE '\''lead_intakes'\'';
"
'
```

## Step 4: Service Registry Gates

```bash
curl -fsS http://127.0.0.1:18000/api/v1/services >/tmp/services-v1.3.1-phase-a.json
curl -fsS http://127.0.0.1:18000/api/v1/services/augustine.en/version >/tmp/service-version-augustine.json
curl -fsS http://127.0.0.1:18000/api/v1/services/augustine.en/metadata >/tmp/service-metadata-augustine.json
```

Expected:
- `/api/v1/services` returns `items` + `count`
- `service_version` is present
- `metadata` includes both author profile fields and additive service fields

## Step 5: Intake Route Gate

Avoid synthetic lead creation in prod. Verify route presence through the OpenAPI contract:

```bash
curl -fsS http://127.0.0.1:18000/api/openapi.json >/tmp/openapi-v1.3.1-phase-a.json
python3 - <<'PY'
import json
data = json.load(open('/tmp/openapi-v1.3.1-phase-a.json'))
print('/v1/intake' in data.get('paths', {}))
PY
```

Expected output:
- `True`

## Step 6: Readiness Gates

```bash
curl -fsS http://127.0.0.1:18000/api/healthz
curl -fsS http://127.0.0.1:18000/api/v1/authors >/dev/null
curl -fsS http://127.0.0.1:8086/api/clock >/dev/null
curl -fsSI https://pericopeai.com | sed -n '1,12p'
curl -fsSI https://truevineos.cloud | sed -n '1,12p'
```

## Step 7: Rollback

1. Checkout the previous `AugustineService` release commit on prod.
2. Rebuild only the API:

```bash
cd "$FPR_ROOT"
$COMPOSE up -d --build pericopeai-api
```

3. Re-run Step 3 and Step 6.

## Release Sign-Off

Approve this slice only if all are true:

1. `create_tables.py` completed successfully.
2. `service_catalog`, `service_versions`, and `lead_intakes` exist.
3. `/api/v1/services` and `/api/v1/services/augustine.en/version` return `200`.
4. `/v1/intake` is present in OpenAPI.
5. `GET /api/healthz` returns healthy.
6. No blocking logs in `pericopeai-api`.
