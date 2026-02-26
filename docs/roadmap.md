# PericopeAI — Semantic Versioned Feature Roadmap

**Status:** Strawman  
**Purpose:** Planning, alignment, and sequencing  
**Note:** This roadmap is provisional and intended to evolve.

---

## Semantic Versioning Philosophy

- **MAJOR** — Changes system guarantees, governance, or meaning
- **MINOR** — Adds capability without breaking existing behavior
- **PATCH** — Fixes, performance, or UX refinements only

PericopeAI is treated as a **platform and framework**, not just a website.

---

## v0.x — Pre-Stability (Exploration / Internal Use)

> APIs and behavior are unstable. Breaking changes allowed.

### v0.1.0 — Core Existence
**Goal:** System runs end-to-end.

- FastAPI backend
- Single persona support
- Static corpus ingestion
- Basic RAG pipeline
- Minimal web UI

**Definition of Done**
- User can ask questions and receive grounded responses
- System runs reliably without manual steps

---

### v0.2.0 — Multiple Personas
**Goal:** Persona abstraction exists.

- Persona abstraction layer
- Multiple personas selectable
- Separate corpora per persona
- Persona-specific prompt scaffolding

---

### v0.3.0 — Deterministic Grounding
**Goal:** Reduce ambiguity and prompt leakage.

- Corpus chunking standards
- Retrieval constraints
- Early provenance markers (internal)
- Improved grounding consistency

---

## v1.0.0 — Stable Core

> Safe to build on. Behavior is predictable.

### v1.0.0 — Persona Stability
**Goal:** Personas are repeatable and defensible.

- Formal persona specification template
- Corpus eligibility rubric
- Clear separation of:
  - persona rules
  - grounding corpus
  - reference material
- Repeatable persona creation workflow

**Guarantees**
- Personas behave consistently
- Adding a persona does not alter existing personas

---

## v1.1.x — Transparency & Control (Backward Compatible)

### v1.1.0
**Goal:** User understands how answers are produced.

- Persona modes (e.g. interpretive, analytical)
- Epistemic labeling:
  - textual
  - interpretive
  - speculative
- Optional citations

### v1.1.1 – v1.1.x
- UX refinements
- Performance improvements
- Bug fixes only

### v1.1.2 — Author Context Header (DB-Backed)
**Goal:** Show grounded author context immediately when a persona is selected.

- Add a top-of-chat UI element that updates on persona selection
- Display:
  - selected author name
  - author summary/description
  - authoritative books/works list
- Data source requirements:
  - author identity and summary from author info in DB
  - books/works list from book metadata in DB
  - no hardcoded FE author/book lists
- API support:
  - endpoint (or extension) that returns author profile + books metadata in one payload
  - stable ordering for books list
  - caching headers for read performance
- Technical requirements:
  - add relational catalog tables for authors and author_books (or equivalent normalized model)
  - add migration/seed job to populate catalog tables from canonical corpus sources
  - runtime reads for this header must come from DB-backed catalog queries
  - file-only runtime sources (`author_index.json`, `book_metadata.json`) are not compliant for this feature
  - add contract tests that fail if API returns empty books for a valid production-visible author
- UX behavior:
  - updates instantly when dropdown selection changes
  - loading and empty-state handling
  - hidden for invalid/unknown author selections

**Definition of Done**
- Selecting an author updates the header with DB-backed author + books data.
- Header data matches backend metadata for the selected author.
- Works for all production-visible authors (including newly added authors) without FE code changes.

---

## v1.2.x — Memory (Scoped and Explicit)

### v1.2.0
**Goal:** Continuity without drift.

- Session-scoped memory
- Persona-isolated memory
- Explicit memory boundaries

### v1.2.1+
- Memory inspection
- Reset / disable controls

**Constraint**
- No silent or implicit long-term memory

---

## v1.3.x — Cross-Reference Intelligence (Backward Compatible)

### v1.3.0
**Goal:** Cross-reference scripture, Church Fathers, and works as first-class data.

- Canonical reference normalization:
  - Bible refs (book/chapter/verse)
  - Author/work IDs
  - Segment IDs (`author/source/chapter/position`)
- Cross-reference index/graph:
  - author -> Bible passage
  - author -> author
  - author -> work
  - Bible passage -> Bible passage
- Reference types:
  - explicit citation
  - quoted text
  - mention
  - allusion (confidence-scored)
- Query surfaces:
  - API endpoints for forward and reverse lookup
  - UI panel for "Referenced Scripture" and "Related Authors/Works"
- Governance:
  - evidence snippet and confidence on every derived reference
  - versioned extraction runs for reproducibility

**Definition of Done**
- A user can open a response and see indexed cross-references.
- A user can query reverse links (for example: who references Genesis).
- References are exportable and traceable to source segments.

---

## v2.0.0 — Governance & Auditability (Breaking)

> Institution-ready. Auditable and explainable.

### v2.0.0
- Corpus versioning
- Prompt and configuration diffing
- Response traceability
- Admin audit surfaces
- Best-effort reproducibility

**Breaking Rationale**
- Governance changes system guarantees

---

## v2.1.x — Platform Hardening

- Role-based admin access
- Read-only observability
- Exportable logs and configs
- Deployment profiles (local, VPS, institutional)

---

## v3.0.0 — Platformization (Optional Future)

> PericopeAI as a framework.

- Persona registry / marketplace
- Public API contracts
- Plugin architecture
- Multi-tenant support

**Breaking by design**

---

## Explicit Non-Goals

- Growth hacking
- Social features
- Mass consumer optimization
- Opaque or persuasive AI behavior

PericopeAI prioritizes **intellectual integrity, transparency, and control**.
