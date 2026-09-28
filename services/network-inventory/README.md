# Fortess DNA

The readable ontology of Fortress. Reviewed Markdown definitions and live source
observations remain separate, with provenance and an atomically activated graph.

## Runtime

Deployment authority is `workspace-deployment/locks/network-inventory.yaml`.
Only the additive `fortress-network-inventory` Compose project may run this service
on Sextant. Container listener: loopback 18160. No existing stack is changed.
A native read-only Docker agent writes an atomic redacted spool. The browser/API
container has no Docker socket, shell adapter or provider control interface.

Configuration is private JSON mounted at `/config/config.json`; auth stores SHA256
of randomly generated access tokens in a separate file. Configuration includes
`database`, `auth_file`, `origins`, `sources`, `definitions_dir`, and `route`.
Source adapters accept only administrator-enrolled configuration. Docker spool,
UniFi paginated GETs, HA registry WebSockets and HTTP MCP metadata lists are supported.
Source errors are reported independently; incomplete runs never remove evidence.

MCP endpoint `/mcp` exposes read-only search, relationships, definitions, source
health and endpoint evidence. It does not execute upstream tools. Definition files
are inert Markdown with safe YAML front matter. Unknown references, duplicate IDs,
unsafe YAML, type mismatches and containment cycles reject candidate compilation.

## Development and checks

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements.lock
PYTHONPATH=. .venv/bin/pytest tests -q
npm ci --prefix frontend
npm run build --prefix frontend
DNA_CONFIG=/private/path/config.json PYTHONPATH=. .venv/bin/python -m inventory
```

Keep definitions, source tokens, runtime databases, inventories and backups out of
this public repository. Only synthetic fixtures belong in tests.

## Current implementation limits

This initial build supplies the ontology compiler, independent assertion layers,
store, graph, UI, proposal decisions, source polling and read-only MCP. It is not
full R01–R38 acceptance. Remaining release gates are tracked on Fortess DNA Project
68 and must be reported with live evidence: event-driven HA/Docker collection,
verified cross-source identity binding/merge-split, complete endpoint route checks,
private Git approval synchronization, source-specific access scopes, full replay
semantics, native client discovery, authoritative-source adapters, TLS/DNS access,
backup/rollback drills, performance/browser coverage and the 24-hour soak.
Do not close stories solely because this container is running.
