# Epic: Identity, Authentication, and Customization

## Epic Identity

- Epic ID: `EPIC-IAC-001`
- Status: `Proposed`
- Date: `2026-02-28`
- Target Window: `v1.2.x`
- Scope Type: `Cross-project (AugustineFE + AugustineService + Keycloak integration)`

## Problem Statement

PericopeAI has working Keycloak sign-in, profile sync, and authenticated history, but identity and personalization are still fragmented. Guests and signed-in users can chat, but there is no durable, user-controlled customization layer for defaults, UI preferences, or conversation behavior. Authentication works, but we need clearer session/device controls, stronger UX around auth failures, and a unified account model that can support future paid tiers and role-based capabilities.

## Goals

1. Establish a single identity model across guest and authenticated experiences.
2. Harden authentication flows for reliability, clarity, and role safety.
3. Add first-class user customization settings that persist across sessions and devices.
4. Keep backward compatibility for current chat, history, and author/persona flows.

## Non-Goals

1. Replacing Keycloak as the identity provider.
2. Building a full billing/subscription system in this epic.
3. Building enterprise SSO connectors beyond current Keycloak capabilities.
4. Redesigning the entire chat UI outside auth and customization surfaces.

## In Scope

1. Identity and account baseline:
   - Unified `me` profile contract for frontend and backend.
   - Explicit guest-to-auth merge behavior for session continuity.
   - Consistent user identifiers for analytics and persistence.
2. Authentication hardening:
   - Reliable login/logout/refresh behavior and clear error states.
   - Role-based API enforcement for protected routes.
   - Session visibility and revocation controls for users.
3. Customization foundation:
   - Persisted user preferences for persona defaults and chat behavior.
   - Persisted UI preferences (layout density, reference panel defaults, optional motion toggle).
   - Safe fallback behavior when preferences are missing or invalid.

## User Stories

1. As a guest user, I can chat immediately and keep temporary local preferences.
2. As a signed-in user, my preferences sync and apply automatically on every device.
3. As a signed-in user, I can edit my profile and default persona behavior without touching raw settings files.
4. As a signed-in user, I can review and revoke active sessions/devices.
5. As an operator, I can distinguish authentication failures from authorization failures from service outages.

## Product Requirements

1. New account endpoints:
   - `GET /api/v1/me`
   - `PUT /api/v1/me`
2. New preference endpoints:
   - `GET /api/v1/me/preferences`
   - `PUT /api/v1/me/preferences`
3. Session management endpoints:
   - `GET /api/v1/me/sessions`
   - `DELETE /api/v1/me/sessions/{session_id}`
4. Guest merge behavior:
   - On successful auth, local guest preferences and recent session metadata are merged with server profile using explicit precedence rules.
5. Compatibility requirement:
   - Existing endpoints (`/api/v1/chat`, `/api/v1/history`, `/api/v1/user/profile/sync`, `/api/v1/authors`, `/api/v1/authors/{slug}/profile`) remain functional during rollout.

## Data and Schema Requirements

1. Add `user_preferences` table keyed by `user_id`.
2. Add `user_sessions` table for visible/revocable session records.
3. Store preference payload with schema versioning for safe migrations.
4. Add indexes on `user_id`, `updated_at`, and active session fields to keep account views fast.

## Frontend Requirements

1. Add Account Settings route with:
   - profile summary
   - authentication status
   - preference editor
   - active sessions list
2. Add preference-aware initialization on app load.
3. Add explicit auth error UX for `401`, `403`, and token-refresh failure.
4. Preserve guest mode when auth is disabled or unavailable.

## Security and Reliability Requirements

1. All `me` and preferences endpoints require valid bearer token.
2. JWT validation enforces issuer, audience, expiry, and signature.
3. Session revocation is auditable and reflected quickly in UI.
4. Preference writes are validated server-side against allowed keys and types.
5. No sensitive tokens or PII are written to client logs.

## Observability Requirements

1. Emit structured events for login success/failure, refresh failure, preference read/write, and session revoke.
2. Add dashboard counters for auth errors by status code (`401`, `403`, `5xx`).
3. Add latency/error SLO tracking for `me` and preferences endpoints.

## Milestones

1. Milestone A: Identity contract and schema
   - finalize `me` API contract
   - add DB tables and migrations
2. Milestone B: Auth hardening and session controls
   - session list/revoke APIs
   - frontend auth-state resilience
3. Milestone C: Customization features
   - preferences API and settings UI
   - default persona and UI behavior persistence
4. Milestone D: Rollout and hardening
   - migration and backfill
   - metrics and alerting
   - release gate validation

## Definition of Done

1. Authenticated users can view and edit account profile and preferences in UI.
2. Preferences persist across reloads and across at least two distinct sessions/devices.
3. Users can list and revoke active sessions successfully.
4. Auth error states are differentiated in UI and logs.
5. Existing chat/history/persona flows remain backward compatible.
6. Automated tests cover happy paths and failure paths for new endpoints and UI flows.
7. Runbooks and docs are updated in canonical docs with rollout and rollback steps.

## Risks and Mitigations

1. Risk: preference-schema drift between FE and API.
   Mitigation: enforce shared schema version and server-side validation.
2. Risk: regressions in token refresh behavior.
   Mitigation: integration tests for refresh lifecycle and forced-expiry scenarios.
3. Risk: guest-to-auth merge conflicts.
   Mitigation: deterministic merge rules and explicit telemetry for conflict cases.
4. Risk: session revoke race conditions.
   Mitigation: idempotent revoke endpoint and eventual-consistency UI messaging.

## Dependencies

1. Keycloak realm/client configuration remains authoritative.
2. AugustineService DB migrations and deployment pipeline.
3. AugustineFE route and settings UI additions.
4. Observability plumbing for auth and preference metrics.

## Open Questions

1. Which preference keys are launch-critical for `v1.2.x` versus deferred?
2. Should guest-session merge default to server-wins or client-wins per field?
3. Do we require admin-facing tools for manual session invalidation in this epic?

## Execution Companion Docs

1. [Testing and Hardening Plan: Identity/Auth/Customization](identity-auth-customization-testing-hardening.md)
2. [PericopeAI Author Test Runner](testing.md)
3. [Hardening Plan (PericopeAI + AMA on Contabo)](hardening-plan.md)
