# Sextant remote observer

Prepared Contabo-side config for remote access to the Sextant observer at
`https://sextant.lecrowndevelopment.com`. This repository is public. The
change does not deploy, does not change DNS, and does not contain secrets,
tokens, client secrets, cookie secrets, private keys, passwords, or private
LAN addresses. Go-live stays blocked until the gate below is open.

The companion deployment lock is `locks/sextant-remote.yaml` in the
benlagrone/Fortress `workspace-deployment` repository. That lock is a parallel
pull request. It is not in this repository.

This edge is not part of the PericopeAI stack. Do not add it to
`docker-compose.pericope.yml`, and do not change that stack's project name,
network, or ports.

## Architecture

```text
browser
  -> https://sextant.lecrowndevelopment.com
  -> host nginx on Contabo
       /oauth2/            -> 127.0.0.1:18046  oauth2-proxy
       /                   -> auth_request /oauth2/auth, then 127.0.0.1:18219
       /status             -> bearer map, then 127.0.0.1:18219
  -> reverse SSH tunnel, loopback on both ends
  -> observer on fortress-sextant at 127.0.0.1:18219

bot
  -> GET /status with its own Bearer token
  -> nginx map /etc/nginx/sextant-status-tokens.map
  -> same loopback tunnel
```

oauth2-proxy is Keycloak OIDC against
`https://auth.pericopeai.com/realms/fortress`, client `sextant-remote`, realm
role `sextant-operator`, PKCE `S256`. The browser session cookie is secure,
SameSite lax, and scoped to `sextant.lecrowndevelopment.com`.

`/status` does not use the browser login. One Bearer token per bot is an
exact `Authorization` match in the host map. The map is root:root mode 0600
and is not in git. GET and HEAD are limited to 30 requests per minute per
client address, burst 10. Any other method is denied.

These observer routes are exact-match 404s and do not redirect to login:

- `/healthz`
- `/v1/reports/feed.json`
- `/v1/production/portfolio/summary.json`

Arcade polls with `fetch`. The vhost does not upgrade WebSocket connections.

Host nginx publishes 80 and 443 only. oauth2-proxy is published on
`127.0.0.1:18046`. The tunnel listens on `127.0.0.1:18219`. `GatewayPorts` on
the Contabo sshd stays `no`.

Port 80 serves `/.well-known/acme-challenge/` from `/var/www/letsencrypt` and
answers every other request with 308 to HTTPS. The bootstrap vhost is the
HTTP-only file used before the certificate exists. It serves the same webroot
and does not proxy the observer. Remove it when the HTTPS vhost is installed.
Do not enable both copies of the server name.

The prod registry entry `sextant-remote-edge` is `enabled: false`. That is
the registry's disabled flag; this schema has no separate planned value. The
entry is planned, not active. Do not flip it until the gate is open and the
smoke checks pass.

## Go-live gate

Do not execute the steps below until all three are true:

1. The Contabo root password has been rotated out of band.
2. SSH to that host is key-only.
3. Benjamin has approved go-live.

Do not record the new password, the tunnel private key, the client secret,
the cookie secret, or a bot token in git, in a ticket, or in a shell log.
FortressPhronesis holds the oauth2-proxy secrets and the status-token map.

## Ordered go-live steps

Run these on the Contabo host unless a step says fortress-sextant. Reload
nginx only after `nginx -t` succeeds. Do not edit other sites.

1. **DNS.** In the existing Google Cloud DNS zone, add an A record for
   `sextant.lecrowndevelopment.com` to the public address already used by
   `lecrowndevelopment.com`. Do not copy that address into git.

2. **Bootstrap vhost.**

   ```bash
   sudo install -d -m 755 /var/www/letsencrypt /etc/nginx/sites-available /etc/nginx/sites-enabled
   sudo install -m 644 deploy/nginx/sextant.lecrowndevelopment.com.bootstrap.conf \
     /etc/nginx/sites-available/sextant.lecrowndevelopment.com
   sudo ln -sfn /etc/nginx/sites-available/sextant.lecrowndevelopment.com \
     /etc/nginx/sites-enabled/sextant.lecrowndevelopment.com
   sudo nginx -t && sudo nginx -s reload
   ```

3. **Certificate.** Webroot only:

   ```bash
   sudo certbot certonly --webroot -w /var/www/letsencrypt \
     -d sextant.lecrowndevelopment.com
   ```

   Use the certbot account already registered on the host.

4. **HTTPS vhost.** The HTTPS file includes
   `/etc/nginx/sextant-status-tokens.map`, so a deny-all stub has to exist
   before `nginx -t`. Real bot tokens come later, in the token-map step.
   Install the stub, then replace the bootstrap file. The HTTPS file also
   owns port 80 (ACME plus the 308). Disable the bootstrap copy by
   overwriting the same `sites-available` path; do not leave a second
   enabled file for this server name.

   ```bash
   sudo install -o root -g root -m 600 /dev/stdin /etc/nginx/sextant-status-tokens.map <<'EOF'
   map $http_authorization $sextant_status_ok {
       default 0;
   }
   EOF
   sudo install -m 644 deploy/nginx/sextant.lecrowndevelopment.com.conf \
     /etc/nginx/sites-available/sextant.lecrowndevelopment.com
   sudo ln -sfn /etc/nginx/sites-available/sextant.lecrowndevelopment.com \
     /etc/nginx/sites-enabled/sextant.lecrowndevelopment.com
   sudo nginx -t && sudo nginx -s reload
   ```

5. **Edge compose.** Copy the env example into place, generate the cookie
   secret there, and leave the client secret empty until the Keycloak step.
   oauth2-proxy will not be healthy until both values are single lines in
   that file. Publish stays on `127.0.0.1:18046`.

   ```bash
   sudo install -d -m 700 /etc/fortress
   sudo install -o root -g root -m 600 deploy/sextant-remote/.env.example \
     /etc/fortress/sextant-remote-edge.env
   openssl rand -base64 32 | sudo python3 -c '
   import pathlib, sys
   secret = sys.stdin.read().strip()
   if not secret or any(ch.isspace() for ch in secret):
       sys.exit("refusing cookie secret")
   path = pathlib.Path("/etc/fortress/sextant-remote-edge.env")
   lines = [ln for ln in path.read_text().splitlines()
            if not ln.startswith("OAUTH2_PROXY_COOKIE_SECRET=")]
   lines.append("OAUTH2_PROXY_COOKIE_SECRET=" + secret)
   path.write_text("\n".join(lines) + "\n")
   path.chmod(0o600)
   print("stored OAUTH2_PROXY_COOKIE_SECRET")
   '
   sudo docker compose -p sextant-remote-edge -f docker-compose.sextant-remote-edge.yml up -d
   ```

   The image is pinned to `quay.io/oauth2-proxy/oauth2-proxy:v7.15.6`.
   Inside the container the process listens on `0.0.0.0:4180` so the
   published port can reach it. The host bind is loopback only.

6. **Keycloak.** Follow
   [deploy/keycloak/README-fortress-realm.md](../deploy/keycloak/README-fortress-realm.md).
   Confirm which Keycloak instance serves `auth.pericopeai.com` before
   import. Create the one operator Benjamin names, assign
   `sextant-operator`, and store the generated client secret in the host env
   file. Then run the compose command from step 5 again so the container
   reads it.

7. **Tunnel.** On fortress-sextant, generate an ed25519 key for this tunnel
   only (`ssh-keygen -t ed25519`). The private key stays on that Mac, mode
   600, and is never committed. Put the public key in the dedicated non-root
   Contabo user's `authorized_keys`, using
   [deploy/sextant-remote/authorized_keys.example](../deploy/sextant-remote/authorized_keys.example).
   Confirm `GatewayPorts` is unset or `no`, and that `AllowTcpForwarding`
   allows remote forwards. Pin the server host key, substitute every
   `REPLACE_ME` in
   [the LaunchAgent example](../deploy/sextant-remote/com.fortress.sextant.contabo-observer-tunnel.plist.example),
   install it under `~/Library/LaunchAgents/`, and load it:

   ```bash
   mkdir -p "$HOME/Library/Logs" "$HOME/Library/LaunchAgents"
   launchctl bootstrap "gui/$(id -u)" \
     "$HOME/Library/LaunchAgents/com.fortress.sextant.contabo-observer-tunnel.plist"
   ```

   The forward is `127.0.0.1:18219` on Contabo to `127.0.0.1:18219` on
   fortress-sextant, where the observer already listens. `autossh -M 0 -N`
   is what keeps it a forward with no shell.

8. **Token map.** Replace the deny-all stub with one line per bot from
   [deploy/nginx/sextant-status-tokens.map.example](../deploy/nginx/sextant-status-tokens.map.example).
   Delete the `REPLACE_ME` line. Install root:root mode 0600 at
   `/etc/nginx/sextant-status-tokens.map`. Do not print the file.

   ```bash
   sudo install -o root -g root -m 600 /path/to/host-only-map \
     /etc/nginx/sextant-status-tokens.map
   sudo nginx -t && sudo nginx -s reload
   ```

9. **Smoke.** From a machine that should not echo the token:

   Export `SEXTANT_STATUS_TOKEN` in the shell without printing it, then run:

   ```bash
   bash scripts/smoke-sextant-remote.sh
   ```

   Do not pass `--token`, and do not put the token in the command line.
   On the Contabo host, also run:

   ```bash
   bash scripts/smoke-sextant-remote.sh --on-host
   ```

   Expected results:

   - `GET /` without a session is 302 to `https://auth.pericopeai.com/realms/fortress`.
   - `GET /status` without a token is 401.
   - `GET /status` with the token is 200 and the body is JSON.
   - `POST /status` is 403 or 405.
   - `GET /healthz` is 404.
   - `--on-host` reports `127.0.0.1:18046` and `127.0.0.1:18219` and fails if
     either port is bound anywhere else.

   After the smoke passes, and only then, consider flipping
   `sextant-remote-edge.enabled` to `true` in `deploy/environments/prod.yaml`.
   That flip is a separate change. This document does not do it.

## Rollback

Reverse the path. Leave every other site and the PericopeAI stack alone.

1. On fortress-sextant, unload the tunnel:

   ```bash
   launchctl bootout "gui/$(id -u)/com.fortress.sextant.contabo-observer-tunnel"
   ```

2. On Contabo, stop the edge and remove the vhost symlink:

   ```bash
   sudo docker compose -p sextant-remote-edge -f docker-compose.sextant-remote-edge.yml down
   sudo rm -f /etc/nginx/sites-enabled/sextant.lecrowndevelopment.com
   sudo nginx -t && sudo nginx -s reload
   ```

3. Disable the Keycloak client `sextant-remote` (see the realm README). Do
   not delete realm `fortress` unless Benjamin says it has no other use.

4. Remove the DNS A record only if the name should stop resolving. The
   certificate can stay until it expires.

5. Leave `/etc/fortress/sextant-remote-edge.env` and
   `/etc/nginx/sextant-status-tokens.map` in place, mode 0600, or delete them
   on the host. Do not copy them into git. Keep `sextant-remote-edge.enabled`
   false.

## Files

- `deploy/nginx/sextant.lecrowndevelopment.com.conf`
- `deploy/nginx/sextant.lecrowndevelopment.com.bootstrap.conf`
- `deploy/nginx/sextant-status-tokens.map.example`
- `docker-compose.sextant-remote-edge.yml`
- `deploy/sextant-remote/.env.example`
- `deploy/apps/sextant-remote-edge.yaml`
- `deploy/environments/prod.yaml` (`enabled: false`, planned)
- `deploy/keycloak/fortress-realm.example.json`
- `deploy/keycloak/README-fortress-realm.md`
- `deploy/sextant-remote/com.fortress.sextant.contabo-observer-tunnel.plist.example`
- `deploy/sextant-remote/authorized_keys.example`
- `scripts/smoke-sextant-remote.sh`
