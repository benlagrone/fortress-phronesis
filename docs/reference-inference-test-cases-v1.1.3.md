# Reference Inference Test Cases (v1.1.3)

## Purpose

Provide concrete, repeatable UI test cards for:

1. inferred Bible references from answer text and retrieved excerpts
2. cross-reference open behavior in `Related Authors / Works`

## Preconditions

1. Pericope stack running on local dev (`http://localhost:13080`, `http://localhost:18000`)
2. Frontend built from current `AugustineFE/src/App.js`
3. API key configured in `AugustineFE/.env` (`REACT_APP_AUGUSTINE_API_KEY`)

## Test Card 1: Augustine -> Inferred Bible References

1. Persona: `Saint Augustine`
2. Prompt: `Explain Adam fall with scriptural grounding`
3. Expected in answer: references to Genesis passages.
4. Expected in `References`:
   - at least one `Genesis <chapter>:<verse>` row appears
   - row can be inferred even if metadata rows are Augustine source excerpts

Pass:

- `Genesis` citation appears in `References`.

## Test Card 2: Irenaeus -> Non-Bible Persona with Bible Citations

1. Persona: `Irenaeus`
2. Prompt: `Defend apostolic succession and include scripture citations.`
3. Expected in `References`: Bible rows appear (examples observed: `Numbers 16:33`, `Acts 1:20-26`).

Pass:

- at least one Bible citation row appears in `References`.

## Test Card 3: Matched Work Open Behavior

1. In `Related Authors / Works`, click `Open` on any matched work.
2. Expected detail state:
   - `Referenced Work Excerpt` is shown
   - excerpt text is populated from `book_partial`
   - no `Switch to ...` action appears in this detail card

Pass:

- excerpt loads successfully and `Switch to ...` is absent.

## Test Card 4: Regression for Existing Metadata References

1. Persona: `John`
2. Prompt: `what can you say about Jesus relationship with Philip?`
3. Expected:
   - John reference rows appear as before
   - `Expand` still works for metadata-backed rows

Pass:

- metadata reference expansion behavior is unchanged.

## Test Card 5: Known Future Scope (Expected Gap Today)

1. Persona: `socrates` (if available)
2. Prompt: `Compare your position with Plato in Republic`
3. Current expectation:
   - cross-author/work inference (`Socrates -> Plato -> Republic`) is roadmap scope (`v1.3.2`) and may not appear yet

Pass (for current release):

- behavior documented as not-yet-implemented, no regression/crash.
