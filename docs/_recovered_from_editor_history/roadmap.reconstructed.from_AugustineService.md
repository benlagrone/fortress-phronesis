
# PericopeAI & PhronēsisAI Roadmap

## Phase 1 – Current Backend & Frontend Foundations (PericopeAI.com)
**Goal:** Stable persona-driven chatbot with RAG, session persistence, and working UI.

### Backend (AugustineService)
- [x] FastAPI endpoints (`/api/v1/chat`, `/api/v1/book`, `/api/v1/session`, `/api/v1/end_session`, `/ask`, `/tweet`, etc.)
- [x] RAG with Augustine texts (scraping, preprocessing, Chroma/HuggingFace embeddings)
- [x] MySQL conversation history (`chat_ui_history`, `chat_sessions`)
- [x] Ollama (Mistral) persona model with pastoral tone + theological references
- [x] OpenAI API routing support
- [x] Twitter posting + Stable Diffusion image generation

### Frontend
- [x] React 19 chat UI with persona/mode selectors
- [x] Session ID tracking and memory test button
- [x] Side panel for book/chapter references
- [x] Loading and error states

---

## Phase 2 – PericopeAI Feature Expansion
**Goal:** Make PericopeAI an extensible multi-persona platform.

### Backend
- [ ] Add **Freud** persona (parallel RAG + model prompt)
- [ ] Refactor RAG to support **multiple corpora** (Bible, Church Fathers, Freud, etc.)
- [ ] Integrate Bible LLM (LoRA fine-tuned or retrieval-augmented)
- [ ] Inline citations with clickable footnotes
- [ ] Optional streaming responses (SSE/WebSockets)

### Frontend
- [ ] Persona list expansion (Freud, Bible, Aquinas, etc.)
- [ ] Citation footnotes inline with messages
- [ ] UI toggle to **include/exclude governance filter** (see Phase 3)
- [ ] Local storage for chat history when not logged in

---

## Phase 3 – PhronēsisAI Integration (Governance Layer)
**Goal:** Add moral/wisdom framework evaluation of chatbot responses.

### Governance Engine
- [ ] Core `evaluate()` logic for scoring text against a **ruleset**
- [ ] Ruleset YAML format (e.g., `augustine.yaml`, `daoist.yaml`)
- [ ] Verdict object (`score`, `violations`, `commentary`, `recommendation`)
- [ ] Side-by-side framework A/B scoring (e.g., Augustine vs Daoism)
- [ ] Public scorecards for transparency

### Integration
- [ ] Hook PericopeAI responses through selected governance filter(s)
- [ ] Display governance verdicts alongside LLM output
- [ ] Governance toggle in frontend controls

---

## Phase 4 – Open-Source & Institutional Build-Out
**Goal:** Make governance system open, forkable, and institutionally credible.

- [ ] Publish `phronesis-core` repo with governance engine + rulesets
- [ ] Contributor guidelines + ruleset submission template
- [ ] Versioned canonical rulesets (core vs. community forks)
- [ ] Public governance leaderboard (score comparisons for models)
- [ ] Outreach to universities, think tanks, seminaries

---

## Phase 5 – SaaS & API Commercialization
**Goal:** Offer hosted governance/compliance as a service.

- [ ] Hosted API for governance evaluation (`/evaluate`)
- [ ] Phronēsis Score™ reports (JSON + PDF)
- [ ] Multi-framework A/B testing as a product
- [ ] Dashboard for bulk evaluation & compliance exports
- [ ] Integration examples for 3rd-party LLMs and chatbots

---

## Phase 6 – Real “Open-Source ESG” Layer
**Goal:** Extend PhronēsisAI into a transparent, tradition-grounded governance standard.

- [ ] Expand rule library (Stoicism, Daoism, Natural Law, etc.)
- [ ] Publish open governance datasets + verdict logs
- [ ] Public debate/commentary tools for refining rulesets
- [ ] Governance certification badges (“Governed by PhronēsisAI v1”)
- [ ] Partnerships with orgs needing traceable ethics frameworks
