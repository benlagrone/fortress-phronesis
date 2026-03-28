# Pericope API Public Deploy Proof — 2026-03-27

- Date: 2026-03-27
- Control-plane workflow: `Deploy Pericope API`
- Successful run: `23670156037`
- Run URL: `https://github.com/benlagrone/fortress-phronesis/actions/runs/23670156037`
- AugustineService commit deployed: `e4275cc`

## Public Verification

- `GET https://pericopeai.com/api/v1/services/augustine.en/version` -> `200`
- `GET https://pericopeai.com/api/v1/services/augustine.en/versions` -> `200`

## Public Response Snapshot

- `service_id`: `augustine.en`
- `service_version`: `1.0.0`
- `schema_version`: `1`
- `built_at`: `2026-03-27T22:09:07`
- `active_version`: `1.0.0`
- `rollback_target_version`: `null`
- `count`: `1`

## Closure

Public deploy alignment for `v1.3.1` is complete. The prior public-route gap for `/api/v1/services/{service_id}/versions` is closed.
