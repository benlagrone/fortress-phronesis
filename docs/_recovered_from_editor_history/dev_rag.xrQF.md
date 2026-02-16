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