# Server Environments

Purpose: keep prod/dev/local straight and avoid accidental drift or
cross-environment changes.

## Environments

Prod (vmi2669159)
- Workspace: `/root/workspace`
- Compose file: `fortress-phronesis/docker-compose.pericope.yml`
- Compose project: `fortress-phronesis`
- Ports: API `18000`, FE `13080`, MySQL `3307`
- Network: `fortress-phronesis-net` (compose-managed)

Dev (fortress-phronesis / 192.168.86.23)
- Workspace: `/home/master-benjamin/Projects/pericopeai.com`
- Compose file: `fortress-phronesis/docker-compose.pericope.yml`
- Compose project: `pericope-dev`
- Ports: API `18000`, FE `13080`, MySQL `3307`
- Network: `fortress-phronesis-net` (compose-managed)

Local (macOS)
- Workspace: `/Users/benjaminlagrone/Documents/projects/pericopeai.com`
- API port: typically `8080` (check `docker ps`)
- FE port: `3000` (dev server) or `13080` (compose)

## Repo layout

Each repo has its own `.env`:
- `AugustineCorpus/.env`
- `AugustineService/.env`
- `AugustineFE/.env`

There is no top-level `.env` in `fortress-phronesis`.
For prod, set `ENVIRONMENT=prd` (or `ENV=prd`) in both
`AugustineCorpus/.env` and `AugustineService/.env` to hide `local_only`
authors like "Alpha (Dev)".
You can also force this behavior in API regardless of ENV with:
`HIDE_LOCAL_ONLY=true` in `AugustineService/.env`.

## Pericope stack

Location: `fortress-phronesis/docker-compose.pericope.yml`
- Paths are relative to the compose file (`../AugustineCorpus`,
  `../AugustineService`, `../AugustineFE`).
- `fortress-phronesis-net` is created by compose automatically.
- Internal service DNS: `augustine-corpus-live`, `mysql`.
- Do not use `localhost` inside containers.

Start/stop
```bash
cd /root/workspace/fortress-phronesis
docker compose -p fortress-phronesis -f docker-compose.pericope.yml up -d --build
docker compose -p fortress-phronesis -f docker-compose.pericope.yml ps
```

## Reindex workflow (prod/dev)

```bash
cd /root/workspace/fortress-phronesis
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
  --base-url http://localhost:8080 \
  --question "Summarize the main themes in 3-5 sentences and include citations." \
  --out tests/author-chat-test.jsonl
```

Prod/dev (server):
```bash
mkdir -p /root/workspace/tests
python3 /root/workspace/fortress-phronesis/scripts/test-authors.py \
  --base-url http://localhost:18000 \
  --question "Summarize the main themes in 3-5 sentences and include citations." \
  --out /root/workspace/tests/author-chat-test.jsonl
```

## Troubleshooting

If API cannot reach MySQL:
- Ensure both containers are on `fortress-phronesis-net`.
- Recreate services via compose to restore DNS:
```bash
cd /root/workspace/fortress-phronesis
docker compose -p fortress-phronesis -f docker-compose.pericope.yml up -d --force-recreate mysql pericopeai-api
```
