# UI-006 + UI-007 Public Verification (`2026-03-31`)

Scope closed:
- `UI-006` chat request lifecycle states and explicit `401` / `403` / `504` UX
- `UI-007` responsive layout with desktop right-side context/references panel and mobile single-column chat behavior

## Local verification

- `CI=true npm test -- --watch=false --runTestsByPath src/App.test.js`
  - PASS (`13` tests)
  - Covers:
    - sending state
    - `401` banner with retry affordance
    - `403` banner without retry affordance
    - `504` timeout -> retry -> recovered state
    - resume-session affordance
    - inferred References fallback
- `npm run build`
  - PASS
  - Existing warning remains: `submitPromptText` changes a `useEffect` dependency in `src/App.js`

## Public stack verification

- `https://pericopeai.com` serves:
  - JS bundle: `/static/js/main.18ad2e51.js`
  - CSS bundle: `/static/css/main.b0b78c80.css`
- Public JS bundle contains:
  - `Authentication Required`
  - `Access Denied`
  - `Upstream Timeout`
  - `Response Received`
  - `Resume session`
  - `References`
- Public CSS bundle contains the desktop/mobile layout classes for:
  - `chat-layout`
  - `chat-status`
  - `references`
  - `crossref-panel`

## Closeout

`v1.1.4` UI carry-over is live on the public stack and is no longer blocking forward roadmap work.
