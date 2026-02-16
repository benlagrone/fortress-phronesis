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