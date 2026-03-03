# Testing and Hardening Plan: Identity/Auth/Customization

## Document Identity

- Plan ID: `IAC-TH-001`
- Date: `2026-02-28`
- Epic: [Epic: Identity, Authentication, and Customization](epic-identity-auth-customization.md)
- Applies To:
  - `AugustineService`
  - `AugustineFE`
  - Keycloak integration path

## Purpose

Define mandatory testing and hardening work to ship identity/auth/customization safely in `v1.2.x`.

## Scope

1. New endpoints:
   - `/api/v1/me`
   - `/api/v1/me/preferences`
   - `/api/v1/me/sessions`
2. Existing auth-dependent flows:
   - `/api/v1/user/profile/sync`
   - `/api/v1/history`
   - `/api/v1/chat` with bearer token behavior
3. Frontend flows:
   - login/logout
   - token refresh lifecycle
   - account settings and preference persistence
   - guest-to-auth merge behavior

## Test Strategy

### 1) Unit Tests (Backend)

1. JWT and claims handling:
   - valid token accepted
   - expired token rejected
   - issuer/audience mismatch rejected
2. Preference validation:
   - unknown keys rejected
   - invalid types rejected
   - schema-version mismatch handled safely
3. Session revoke semantics:
   - revoke target exists
   - idempotent revoke on already-revoked session
   - user cannot revoke another user session

### 2) Integration Tests (Backend + DB)

1. `GET /api/v1/me` returns consistent user contract.
2. `PUT /api/v1/me/preferences` persists and is readable across requests.
3. `GET /api/v1/me/sessions` returns current active sessions only.
4. `DELETE /api/v1/me/sessions/{session_id}` invalidates target session state.
5. Backward compatibility:
   - `/api/v1/chat`, `/api/v1/history`, `/api/v1/authors`, `/api/v1/authors/{slug}/profile` remain stable.

### 3) Frontend Tests

1. Component tests:
   - Account Settings renders loading, success, and error states.
   - Preference editor performs optimistic/confirmed state transitions.
2. App-state tests:
   - app boot reads persisted preferences and applies defaults.
   - invalid preference payload falls back to safe defaults.
3. Error UX tests:
   - distinct behavior/messages for `401`, `403`, and timeout.

### 4) End-to-End Tests (Browser)

1. Guest flow:
   - start as guest, change local preferences, chat successfully.
2. Auth flow:
   - sign in via Keycloak, profile sync succeeds, protected routes accessible.
3. Merge flow:
   - guest preferences merge on sign-in with deterministic precedence.
4. Session management:
   - view active sessions, revoke one session, confirm expected effect.
5. Regression flow:
   - existing chat/history/persona behavior unchanged for authenticated user.

### 5) Security Tests (Negative/Abuse Cases)

1. API access without token returns `401`.
2. API access with insufficient role returns `403`.
3. Cross-user access attempts to `me/sessions` resources fail.
4. Malformed JSON and oversized payloads fail with controlled errors.
5. Token replay and stale refresh token behavior are logged and rejected.

### 6) Non-Functional Tests

1. Performance:
   - p95 latency targets for `GET /me` and `GET /me/preferences` under representative load.
2. Reliability:
   - token refresh failure recovery path does not dead-loop login attempts.
3. Migration safety:
   - preferences table migration is rollback-tested in staging.

## Hardening Requirements

### 1) Auth and Session Controls

1. Enforce issuer/audience/signature/expiry checks on all protected endpoints.
2. Enforce role checks consistently on account endpoints.
3. Store and enforce session status (`active`, `revoked`, `expired`) server-side.
4. Ensure revoke is audit-logged with actor, timestamp, and target session.

### 2) API and Input Hardening

1. Strict input schemas for profile and preference writes.
2. Payload size limits for update endpoints.
3. Rate limiting on auth-sensitive routes (`/me`, `/me/preferences`, `/me/sessions`).
4. Consistent error response contract without token/PII leakage.

### 3) Data Protection

1. Minimize stored PII to required profile fields only.
2. Encrypt secrets at rest in env/secret management flow.
3. Keep DB users least-privilege for account tables.
4. No auth tokens in client storage beyond Keycloak adapter expectations.

### 4) Frontend Hardening

1. Do not render privileged settings until auth state is confirmed.
2. Clear sensitive in-memory state on logout.
3. Guard all account routes against unauthenticated access.
4. Add anti-regression checks for auth-disabled mode behavior.

### 5) Operational Hardening

1. Structured logs for auth events:
   - login success/failure
   - token refresh failure
   - preference write
   - session revoke
2. Alerting thresholds for spikes in `401`, `403`, and auth-related `5xx`.
3. Add rollback runbook steps specific to account schema migrations.

## Release Gates (Must Pass)

1. Automated test gate:
   - unit + integration + FE tests green in CI.
2. E2E gate:
   - guest, auth, merge, revoke flows pass.
3. Security gate:
   - negative auth/authorization tests pass.
4. Compatibility gate:
   - current chat/history/persona flows show no regressions.
5. Observability gate:
   - metrics and logs visible in staging before production promote.
6. Rollback gate:
   - migration rollback drill executed and documented.

## Sign-Off Artifacts

1. CI test report links and summary.
2. E2E run output with pass/fail evidence.
3. Security test checklist and outcomes.
4. Staging metrics screenshots or exported dashboards.
5. Rollback drill log with exact timestamps and steps.

## Execution Checklist

- [ ] Finalize test cases and map each to owner.
- [ ] Implement missing automated tests (backend, frontend, E2E).
- [ ] Add rate limiting and payload limits for account endpoints.
- [ ] Add audit logging for session revoke and preference updates.
- [ ] Run full staging gate suite and collect artifacts.
- [ ] Run production cutover with rollback path pre-validated.
