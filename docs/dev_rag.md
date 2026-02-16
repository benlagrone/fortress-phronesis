Below is a clean handoff you can paste directly into Codex inside VS Code.
It’s written to be executable, scoped, and safe — no wandering, no platform-building.

⸻

HANDOFF: Add Repo-Scoped RAG to PericopeAI

Context
This repo is PericopeAI (Python backend + React frontend).
Goal is to add local, repo-scoped RAG to improve code understanding and refactors inside VS Code.

This is not a full agent.
This is RAG-only: index → retrieve → inject context into prompts.

⸻

Objective

Add a local RAG service that:
	•	indexes this repo only
	•	stores embeddings per-project
	•	exposes a simple HTTP endpoint
	•	can be called from VS Code / Codex prompts

No cloud dependencies required, but OpenAI embeddings are acceptable.

⸻

Constraints (non-negotiable)
	•	One RAG index per repo
	•	Do not mix data from other projects
	•	Do not auto-modify files
	•	RAG returns context only, not patches
	•	Minimal dependencies, Python preferred
	•	Must run locally

⸻

High-Level Design

pericopeai/
  rag/
    ├─ indexer.py        # one-time + incremental indexing
    ├─ server.py         # FastAPI service
    ├─ retriever.py      # vector search
    ├─ config.py
    └─ README.md
  .rag/
    └─ pericopeai/       # local vector store (gitignored)

Use:
	•	Qdrant (local) or Chroma
	•	Chunk size ~800 tokens, overlap ~150
	•	Exclude: node_modules, dist, build, venv, pycache

⸻

Functional Requirements

1. Indexing
	•	Index:
	•	backend Python code
	•	frontend React code
	•	README / docs
	•	Each chunk must store:
	•	file path
	•	language
	•	chunk text

Indexer must support:
	•	full rebuild
	•	re-index changed files only

2. Retrieval
Given a natural language question:
	•	retrieve top 5–7 relevant chunks
	•	return structured context:
	•	file path
	•	excerpt
	•	no summarization yet

3. API
Expose local endpoint:

POST /rag/query
{
  "question": "How does persona selection work?"
}

Response:

{
  "context": [
    { "file": "...", "excerpt": "..." }
  ]
}


⸻

Prompt Contract (important)

Returned context is intended to be injected above the user prompt:

You are working inside the PericopeAI codebase.

Relevant context:
- file: backend/chat/router.py
  excerpt: ...

Task:
<user question>

Do not change this ordering.

⸻

Out of Scope
	•	No UI
	•	No VS Code extension yet
	•	No autonomous file changes
	•	No CI integration
	•	No multi-repo support

⸻

Success Criteria
	•	I can ask:
“Where is persona selection enforced?”
and get accurate file references
	•	Model hallucinations drop noticeably
	•	Index is isolated to this repo
	•	Service runs with one command

⸻

Deliverables
	•	rag/ folder with code
	•	.rag/ added to .gitignore
	•	README explaining:
	•	how to build index
	•	how to run server
	•	example query

⸻

Tone & Style
	•	Prefer clarity over cleverness
	•	Minimal abstractions
	•	Explicit over implicit
	•	Small, readable modules

⸻

Begin with the indexer and retriever. Do not over-engineer.

⸻

If you want, after this is implemented, the next handoff would be:
	•	VS Code command integration
	•	patch-generation layer
	•	test-aware retrieval

But this step is RAG only.

⸻

Implementation Plan (sequence)

1) Scaffolding
	•	Add `rag/` package with `config.py`, `indexer.py`, `retriever.py`, `server.py`, and a `README.md`.
	•	Add `.rag/` to `.gitignore` (local vector store).

2) Config + Filtering
	•	In `config.py`, define repo root, chunking params (size ~800, overlap ~150), and exclusion globs (node_modules, dist, build, venv, __pycache__, .git, *.lock).

3) Indexer
	•	Implement filesystem walk with filters; detect language from extension.
	•	Chunk files (size/overlap above), embed text (OpenAI or local), and upsert into Chroma/Qdrant at `.rag/pericopeai`.
	•	Support full rebuild and incremental mode (mtime/hash) in `indexer.py`.

4) Retriever
	•	`retriever.py`: load vector store, search top k (5–7), return file path, language, and excerpt text (no summarization).

5) API
	•	`server.py`: FastAPI with `POST /rag/query {question}` -> run retriever and return structured context list; add simple health endpoint.

6) CLI Tasks
	•	Add minimal CLI entrypoints in indexer/retriever (e.g., `python -m rag.indexer --full`).
	•	Optionally add a `make rag-index` target for convenience.

7) Docs
	•	Update `rag/README.md` with how to build the index, run the server, and example curl.
	•	Note that context is injected above the prompt per the contract.

8) Validation
	•	Run a full index locally, hit `/rag/query` with a known question (“Where is persona selection enforced?”) and confirm file/excerpt refs are correct.


RAG — what’s implemented
- `rag/` package with config, indexer, retriever, FastAPI server; `.rag/` gitignored for local vector store (Chroma).
- Filters: only code/docs (`.py .js .jsx .ts .tsx .md .json`), excludes corpus dumps and heavy dirs (`node_modules`, dist/build, venv, .git, __pycache__, texts, AugustineCorpus, AugustineService).
- Chunking: 800 tokens, 150 overlap; embeddings: sentence-transformers `all-MiniLM-L6-v2` via Chroma at `.rag/pericopeai`.
- Scripts: `scripts/rag_query.sh` and short wrapper `scripts/rq` save each response to `.rag/context/query-<timestamp>.json` and print a summary for copy/paste or upload.
- Server: FastAPI `/healthz` and `/rag/query` (k default 5).

How to run (local)
1) Env/deps (once): `python3 -m venv venv && source venv/bin/activate && pip install -r rag/requirements.txt`
2) Rebuild index (when code/docs change):  
   `rm -rf .rag/pericopeai && python -m rag.indexer --full`
3) Serve with reload:  
   `PYTHONPATH=. uvicorn rag.server:app --reload --port 8010`
4) Ask and save context:  
   `./scripts/rq "Where is persona selection enforced?"`  
   (JSON lands in `.rag/context/…` for upload; summary prints to terminal.)

Prompt contract (unchanged)
Paste retrieved bullets above your prompt:
```
You are working inside the PericopeAI codebase.

Relevant context:
- file: ...
  excerpt: ...

Task:
<your request>
```

If results are empty or stale
- Ensure server is running on 8010.
- Rebuild index: `rm -rf .rag/pericopeai && python -m rag.indexer --full`.
- Make sure you’re in the repo root and venv is active when running scripts.

---

RAG — what’s implemented
- `rag/` package with config, indexer, retriever, FastAPI server; `.rag/` gitignored for local vector store (Chroma).
- Filters: only code/docs (`.py .js .jsx .ts .tsx .md .json`), excludes corpus dumps and heavy dirs (`node_modules`, dist/build, venv, .git, __pycache__, texts, AugustineCorpus, AugustineService).
- Chunking: 800 tokens, 150 overlap; embeddings: sentence-transformers `all-MiniLM-L6-v2` via Chroma at `.rag/pericopeai`.
- Scripts: `scripts/rag_query.sh` and short wrapper `scripts/rq` save each response to `.rag/context/query-<timestamp>.json` and print a summary for copy/paste or upload.
- Server: FastAPI `/healthz` and `/rag/query` (k default 5).

How to run (local)
1) Env/deps (once): `python3 -m venv venv && source venv/bin/activate && pip install -r rag/requirements.txt`
2) Rebuild index (when code/docs change):  
   `rm -rf .rag/pericopeai && python -m rag.indexer --full`
3) Serve with reload:  
   `PYTHONPATH=. uvicorn rag.server:app --reload --port 8010`
4) Ask and save context:  
   `./scripts/rq "Where is persona selection enforced?"`  
   (JSON lands in `.rag/context/…` for upload; summary prints to terminal.)

Prompt contract (unchanged)
Paste retrieved bullets above your prompt:
```
You are working inside the PericopeAI codebase.

Relevant context:
- file: ...
  excerpt: ...

Task:
<your request>
```

If results are empty or stale
- Ensure server is running on 8010.
- Rebuild index: `rm -rf .rag/pericopeai && python -m rag.indexer --full`.
- Make sure you’re in the repo root and venv is active when running scripts.
