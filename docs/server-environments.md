# Server Environments

Purpose: keep prod/dev/local straight and avoid accidental drift or
cross-environment changes.

## Sacred Rules

1. `.env` files are authoritative. Do not override deployment values with ad-hoc shell exports.
2. Per-repo `.env` ownership is fixed:
   - `AugustineService/.env`
   - `AugustineCorpus/.env`
   - `AugustineFE/.env`
3. Do not add a top-level `fortress-phronesis/.env` deployment control file.
4. Do not change architecture during deployment execution (project name, network name, service topology, live container edits).
5. Frontend `REACT_APP_*` values are build-time; use compose `--env-file` when building frontend.
6. Use direct `docker compose` commands for deploy/update; no wrapper deployment scripts.

## Canonical Paths (Do Not Guess)

Use these exact roots by environment:

Prod (vmi2669159)
- Workspace root: `/root/workspace`
- Stack root: `/root/workspace/fortress-phronesis`
- Compose file: `/root/workspace/fortress-phronesis/docker-compose.pericope.yml`
- Corpus repo: `/root/workspace/AugustineCorpus`
- API repo: `/root/workspace/AugustineService`
- FE repo: `/root/workspace/AugustineFE`

Dev (fortress-phronesis / 192.168.86.23)
- Workspace root: `/home/master-benjamin/Projects/pericopeai.com`
- Stack root: `/home/master-benjamin/Projects/pericopeai.com/fortress-phronesis`
- Compose file: `/home/master-benjamin/Projects/pericopeai.com/fortress-phronesis/docker-compose.pericope.yml`
- Corpus repo: `/home/master-benjamin/Projects/pericopeai.com/AugustineCorpus`
- API repo: `/home/master-benjamin/Projects/pericopeai.com/AugustineService`
- FE repo: `/home/master-benjamin/Projects/pericopeai.com/AugustineFE`

Local (macOS)
- Workspace root: `/Users/benjaminlagrone/Documents/projects/pericopeai.com`
- Stack root: `/Users/benjaminlagrone/Documents/projects/pericopeai.com/fortress-phronesis`
- Compose file: `/Users/benjaminlagrone/Documents/projects/pericopeai.com/fortress-phronesis/docker-compose.pericope.yml`

## Session Path Guard (Run First In Every Shell)

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

Never run deployment commands until `FPR_ROOT` and `COMPOSE_FILE` match the expected environment.

## Environments

Prod (vmi2669159)
- Workspace: `/root/workspace`
- Compose file: `fortress-phronesis/docker-compose.pericope.yml`
- Compose project: `fortress-phronesis`
- Ports: API `18000`, FE `13080`, MySQL `3307`
- Network: `fortress-phronesis-net` (shared external)

Dev (fortress-phronesis / 192.168.86.23)
- Workspace: `/home/master-benjamin/Projects/pericopeai.com`
- Compose file: `fortress-phronesis/docker-compose.pericope.yml`
- Compose project: `fortress-phronesis` (match prod by default)
- Ports: API `18000`, FE `13080`, MySQL `3307`
- Network: `fortress-phronesis-net` (shared external)

Local (macOS)
- Workspace: `/Users/benjaminlagrone/Documents/projects/pericopeai.com`
- Default ports come from `docker-compose.pericope.yml`:
  - API `18000`
  - FE `13080`
  - MySQL `3307`

## Repo layout

Each repo has its own `.env`:
- `AugustineCorpus/.env`
- `AugustineService/.env`
- `AugustineFE/.env`

For prod, set `ENVIRONMENT=prd` (or `ENV=prd`) in both
`AugustineCorpus/.env` and `AugustineService/.env` to hide `local_only`
authors like "Alpha (Dev)".
You can also force this behavior in API regardless of ENV with:
`HIDE_LOCAL_ONLY=true` in `AugustineService/.env`.

## Pericope stack

Location: `fortress-phronesis/docker-compose.pericope.yml`
- Paths are relative to the compose file (`../AugustineCorpus`,
  `../AugustineService`, `../AugustineFE`).
- `fortress-phronesis-net` is a shared external network.
- Internal service DNS: `augustine-corpus-live`, `mysql`.
- Do not use `localhost` inside containers.

Start/stop
```bash
cd <workspace>/fortress-phronesis
docker compose -p fortress-phronesis -f docker-compose.pericope.yml up -d --build mysql augustine-corpus-live pericopeai-api
docker compose -p fortress-phronesis -f docker-compose.pericope.yml up -d --build pericopeai-frontend
docker compose -p fortress-phronesis -f docker-compose.pericope.yml ps
```

If MySQL fails with `Bind for 0.0.0.0:3307 failed: port is already allocated`,
stop the conflicting container first (commonly `pericope-local-mysql-1`) and retry.

## Reindex workflow (prod/dev)

```bash
cd <workspace>/fortress-phronesis
docker compose -p fortress-phronesis -f docker-compose.pericope.yml stop augustine-corpus-live
docker compose -p fortress-phronesis -f docker-compose.pericope.yml rm -f augustine-corpus-live
docker volume ls --format '{{.Name}}' | grep '^fortress-phronesis_corpus_' | xargs -r docker volume rm
docker compose -p fortress-phronesis -f docker-compose.pericope.yml --profile index run --rm pericopeai-indexer
docker compose -p fortress-phronesis -f docker-compose.pericope.yml up -d --build
```

## Upload texts (Mac -> prod)

Sync all corpus text folders (including new books) to prod:
```bash
rsync -av --delete \
  --exclude='.DS_Store' --exclude='._*' \
  /Users/benjaminlagrone/Documents/projects/pericopeai.com/AugustineCorpus/texts/ \
  root@vmi2669159:/root/workspace/AugustineCorpus/texts/
```

Then run the reindex workflow on prod.

## Apocrypha text population (only when missing)

Preflight check:
```bash
python3 fortress-phronesis/scripts/author-preflight.py \
  --texts-root AugustineCorpus/texts --format table
```

Populate missing apocrypha:
```bash
curl -L https://www.gutenberg.org/cache/epub/124/pg124.txt -o /tmp/pg124.txt
python3 AugustineCorpus/scripts/split_gutenberg_kjv_apocrypha.py \
  --input /tmp/pg124.txt --overwrite
```

## Testing

Local:
```bash
fortress-phronesis/scripts/test-authors.py \
  --base-url http://localhost:18000 \
  --question "Summarize the main themes in 3-5 sentences and include citations." \
  --out tests/author-chat-test.jsonl
```

Prod/dev (server):
```bash
mkdir -p <workspace>/tests
python3 <workspace>/fortress-phronesis/scripts/test-authors.py \
  --base-url http://localhost:18000 \
  --question "Summarize the main themes in 3-5 sentences and include citations." \
  --out <workspace>/tests/author-chat-test.jsonl
```

## Troubleshooting

If API cannot reach MySQL:
- Ensure both containers are on `fortress-phronesis-net`.
- Recreate services via compose to restore DNS:
```bash
cd <workspace>/fortress-phronesis
docker compose -p fortress-phronesis -f docker-compose.pericope.yml up -d --force-recreate mysql pericopeai-api
```
