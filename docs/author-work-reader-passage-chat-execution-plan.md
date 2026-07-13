# Author Work Reader and Passage-Anchored Chat Execution Plan

**Status:** planned  
**Owner surface:** AugustineFE, AugustineService, AugustineCorpus, and Fortress Phronesis docs  
**Runtime target:** existing PericopeAI frontend/API/corpus stack  
**Roadmap item:** `v1.3.6 Reader Follow-On -- Author Work Reader and Passage-Anchored Chat`  
**Architecture diagram:** [author-work-reader-passage-chat-architecture.mmd](author-work-reader-passage-chat-architecture.mmd)  
**Deployment note:** This plan does not add a deployed service, public host port, environment variable, or deployment path by itself. Runtime promotion must use the Fortress Phronesis deployment path and update deployment locks if any topology changes are introduced.

## Purpose

PericopeAI should let a user move from author discovery into close reading and
then into same-author conversation about a concrete section of text.

The feature answers one product question:

How can a user open an author's work, select a passage, and ask that same author
about that specific section without losing the existing counsel/chat model?

The answer should be a reader-anchored extension of current chat, not a separate
research product and not an Add Counsel workflow.

## Current Foundations

The feature should build on current surfaces:

- `AugustineFE` already renders author profiles at `/authors/:slug`.
- `AugustineFE` already renders author chat at `/author/:slug` and `/chat`.
- Author profiles already expose `books` from `GET /api/v1/authors/{author_slug}/profile`.
- The UI already calls `POST /api/v1/book_partial` for source-backed excerpt expansion.
- `AugustineService` already proxies `book_partial` to `AugustineCorpus` and falls back to service-local text where needed.
- `AugustineCorpus` already resolves `author_slug + source` and returns position-based text ranges.
- `/api/v2/chat` already accepts additive request fields and returns segmented answers, citations, summary, books, and same-author `follow_up_question`.

## Architecture

The architecture is documented as Mermaid in:

`docs/author-work-reader-passage-chat-architecture.mmd`

The key boundary is that the browser never reads corpus files directly. Public
reader access flows through `AugustineService`, which applies public-author and
access checks before calling `AugustineCorpus`.

## User Flows

### Flow 1: Author Page To Reader

1. User opens `/authors/{author_slug}`.
2. The author profile works list shows a `Read` action beside each work with a
   usable source mapping.
3. User opens `/authors/{author_slug}/works/{source}`.
4. Reader loads an initial stable position range through `POST /api/v1/book_partial`.
5. User can page previous/next ranges without loading the full book by default.

### Flow 2: Chat Page To Reader

1. User opens `/author/{author_slug}` or `/chat`.
2. The selected author context exposes works available for reading.
3. User opens a work reader and can return to the active chat context.
4. Reader deep links preserve author slug, source/work identity, and range.

### Flow 3: Selected Passage To Same-Author Chat

1. User selects one or more reader positions.
2. Reader displays a passage-anchored ask composer.
3. User asks a question.
4. Frontend sends `/api/v2/chat` with the normal chat request plus additive
   `source_context`.
5. API treats the selected passage as primary evidence for that turn.
6. Normal retrieval may add nearby supporting passages.
7. Response stays in the same author voice and may include the existing
   subordinate same-author follow-up segment.

## API Contracts

### Reader Range Request

Initial implementation should continue using `POST /api/v1/book_partial`.

```json
{
  "author_slug": "augustine",
  "book": "Confessions",
  "source": "confessions.txt",
  "chapter": null,
  "page": null,
  "start_position": 42,
  "end_position": 47
}
```

The existing response fields remain backward compatible. Reader-specific
extensions should be additive:

```json
{
  "author_slug": "augustine",
  "book": "Confessions",
  "source": "confessions.txt",
  "reference": "Confessions 8",
  "start_position": 42,
  "end_position": 47,
  "total_positions": 388,
  "previous_position": 37,
  "next_position": 48,
  "entries": [
    {
      "position": 42,
      "reference": "Confessions 8",
      "content": "..."
    }
  ],
  "content": "..."
}
```

`content` stays for existing consumers. `entries`, `total_positions`,
`previous_position`, and `next_position` are reader-oriented additions.

### Passage-Anchored Chat Request

Extend `/api/v2/chat` with additive `source_context`.

```json
{
  "question": "What do you mean here by disordered love?",
  "mode": "conversation",
  "persona": "augustine",
  "source": "reader",
  "source_context": {
    "author_slug": "augustine",
    "book": "Confessions",
    "work": "Confessions",
    "source": "confessions.txt",
    "start_position": 42,
    "end_position": 47,
    "reference": "Confessions 8",
    "content": "..."
  }
}
```

The backend prompt assembly should put selected passage context before normal
retrieval context and should label it as selected source text. It must not treat
position values as canonical scripture verse numbers.

## Implementation Plan

### Phase 0: Contract And Fixture Setup

- Add request/response examples to frontend/service docs.
- Add service model field for optional `source_context` without breaking current
  `/api/v2/chat` clients.
- Add fixture payloads for one non-Bible author work and one scripture-adjacent
  work where position labels can be verified.
- Confirm public-author filtering remains in `AugustineService`, not only in the
  frontend.

Acceptance:

- existing chat requests still validate without `source_context`
- invalid author/source combinations return existing error shapes
- docs define position values as retrieval offsets

### Phase 1: Reader Data Contract

- Extend `AugustineCorpus` `book_partial` response with `entries`,
  `total_positions`, `previous_position`, and `next_position`.
- Preserve existing `content`, `reference`, `chapter`, `verse_start`,
  `verse_end`, `section`, and `testament` response fields.
- Mirror the additive fields through `AugustineService`.
- Keep the service-local fallback shape aligned with corpus response shape.

Acceptance:

- `book_partial` can return a deterministic range for an author/work fixture
- range navigation clamps to valid bounds
- legacy reference expansion still receives `content`

### Phase 2: Frontend Reader Route

- Add `/authors/:authorSlug/works/:source` route in `AugustineFE`.
- Add `Read` actions to the author detail works list.
- Add selected-author works access from the chat context area.
- Render chunks with stable position anchors and previous/next controls.
- Keep full-book loading out of the default path.

Acceptance:

- author detail page links to the reader for works with `source`
- direct reader URL can load from a cold page refresh
- mobile layout keeps reader text, navigation, and ask composer usable

### Phase 3: Passage-Anchored Chat

- Add selected passage/range state to the reader.
- Add a passage-anchored ask composer.
- Send `source_context` to `/api/v2/chat`.
- Update `AugustineService` prompt assembly so selected passage text is primary
  evidence and normal RAG remains supplemental.
- Include selected passage metadata in response trace data without storing raw
  private prompt bodies beyond existing message/citation behavior.

Acceptance:

- anchored question produces a same-author answer that cites or names the
  selected section
- same-author follow-up remains subordinate inside the assistant response
- existing Add Counsel and synthesis flows are unchanged

### Phase 4: Validation And Promotion

- Add unit tests for corpus range response and service passthrough.
- Add frontend tests for author-page reader links, direct route loading, and
  anchored chat request body.
- Run local browser smoke against the Docker-backed API route:
  `REACT_APP_API_BASE_URL=http://localhost:13080/api`.
- Update `deployed-architecture.md`, UI endpoint docs, and smoke checks if
  implementation promotes new runtime behavior.

Acceptance:

- focused unit tests pass in touched repos
- `git diff --check` passes
- local reader smoke proves real author/profile data, not mocked empty rows
- production deploy, if requested later, uses Fortress Phronesis only

## Guardrails

- Do not expose raw corpus files directly from the frontend.
- Do not bypass `AugustineService` public-author filtering.
- Do not reinterpret retrieval positions as canonical verse numbers.
- Do not make `source_context` required for `/api/v2/chat`.
- Do not convert the same-author passage follow-up into Add Counsel.
- Do not add a new deployed service, host port, or deployment path for this
  feature without updating deployment policy, architecture docs, and smoke
  checks in the same change.

## Open Decisions

- Whether reader URLs should use raw `source` filenames, encoded source IDs, or
  stable work IDs once Source Steward metadata is promoted.
- Whether range size should default to paragraph count, approximate character
  count, or section/chapter boundaries.
- Whether selected passage context should be persisted as citations only,
  response-trace metadata, explicit passage references, or all three.
- Whether reader history belongs in normal chat session state or a separate
  lightweight local UI state.
