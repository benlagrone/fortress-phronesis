# Hardening Plan (PericopeAI + AMA on Contabo)

## 1) Secrets & Config
- Rotate all exposed API/DB keys immediately; remove secrets from repos and venvs.
- Store env files root-owned (600), or move to a secret manager; use non-root service users.
- Keep per-service env files separate; document locations and owners.

## 2) Ingress & Nginx
- Deduplicate vhosts; ensure `/chat` proxies to FastAPI (9001 or container), not WordPress.
- Restrict public ports to 80/443; keep app/db on localhost or Docker bridge.
- Add rate limiting, sane proxy timeouts, HSTS, TLS renewal checks.

## 3) Auth / Keycloak
- Pick one Keycloak (prefer Docker + kc-db); decommission the duplicate host instance.
- Back up realms before changes; lock admin creds; review OIDC clients/secrets.
- Keep Keycloak behind Nginx with SSL; verify JWKS endpoints used by apps.

## 4) Database Strategy
- Decide DB locality for PericopeAI/Chat (stay on HostGator or migrate local MariaDB).
- If migrating: provision DB, create least-privilege users, import schema/data, update envs, close inbound 3306.
- Add scheduled backups and restore drills (WordPress DB, Keycloak Postgres, PericopeAI/Chat DB).

## 5) Containerization
- Put PericopeAI API + frontend into docker-compose on a dedicated network; attach Keycloak container.
- Add healthchecks and non-root users in Dockerfiles; pin base images; enable log rotation.
- Stop host uvicorn once containers serve traffic to avoid duplicates.

## 6) App Robustness
- Supervise processes (systemd/compose restart policies); add liveness/readiness endpoints.
- Enforce CORS allowlist; validate inputs; sanitize uploads if any.
- Keep static assets served via nginx; avoid direct app exposure.

## 7) Logging & Monitoring
- Rotate Nginx access/error logs; structure Uvicorn/FastAPI logs; enable DB slow-query logging.
- Set basic alerts/metrics (disk, CPU, memory, HTTP 5xx spikes).

## 8) WordPress Hygiene
- Update core/plugins/themes; remove unused items; tighten file perms.
- Add 2FA/limit login; disable xmlrpc if unused; harden wp-admin access.

## 9) Access Control
- SSH keys only; disable password auth; restrict sudoers; audit users.
- Firewall: allow only SSH/80/443; restrict docker socket access.

## 10) Rollout & Testing
- Stage changes in test compose; run smoke tests (homepage, /chat, /api, Keycloak login).
- Cut over Nginx upstreams with rollback steps ready; verify certs and redirects post-cutover.
