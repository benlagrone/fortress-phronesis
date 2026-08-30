# Rental Finder Public Edge Deployment

This contract publishes the existing private Rental Finder at:

`https://rentalfinder.lecrownproperties.com/`

The public hostname is an authenticated edge, not a public copy of the Fortress control plane.

## Runtime contract

- Public host: `rentalfinder.lecrownproperties.com`
- Public IP: `89.117.151.145`
- TLS termination: host Nginx on the Contabo deployment target
- Authentication: Google OAuth through `oauth2-proxy`
- Allowed identity domain: `lecrownproperties.com`
- OAuth callback: `https://rentalfinder.lecrownproperties.com/oauth2/callback`
- OAuth scopes: `openid profile email`
- Compose project: `rental-finder-edge`
- Compose file: `docker-compose.rental-finder.yml`
- OAuth gateway bind: `127.0.0.1:18044`
- Private upstream: `http://100.100.97.30:8133/rental-finder/`
- API upstream prefix: `http://100.100.97.30:8133/rental-finder/api/`

The Nginx edge maps public `/` requests to the private `/rental-finder/` application path. Browser requests under `/rental-finder/api/` preserve that path when sent to Fortress. Both paths require a valid OAuth session.

## Google Workspace prerequisite

Create a dedicated Google OAuth 2.0 Web application inside a Google Cloud project owned by the LeCrown Google Workspace organization.

Configure:

- App audience: `Internal`
- Authorized redirect URI: `https://rentalfinder.lecrownproperties.com/oauth2/callback`
- Scopes: `openid`, `profile`, `email`

The edge independently requires the verified returned email to end in `@lecrownproperties.com`. The Google client secret and cookie secret stay in GitHub environment secrets and the root-owned server env file. They never enter Rental Finder browser code or the Fortress LAN service.

Required GitHub environment secrets in `benlagrone/fortress-phronesis`:

- `RENTAL_FINDER_GOOGLE_CLIENT_ID`
- `RENTAL_FINDER_GOOGLE_CLIENT_SECRET`
- `RENTAL_FINDER_OAUTH_COOKIE_SECRET`

Generate the cookie secret locally and store only the resulting value in the GitHub secret:

```bash
openssl rand -base64 32 | tr -- '+/' '-_'
```

Deployment SSH secrets use the dedicated `RENTAL_FINDER_DEPLOY_*` family when present and otherwise use the existing `SOLOMONIC_CLOCK_DEPLOY_*` deployment credentials.

## DNS prerequisite

The authoritative DNS provider for `lecrownproperties.com` is currently HostGator. Add:

```text
Type: A
Name: rentalfinder
Value: 89.117.151.145
TTL: 600
```

Do not run the production deployment until public DNS resolves the hostname to the locked Contabo IP. The deployment script fails closed with an HTTP-only 503 bootstrap and does not activate HTTPS when DNS is absent or points elsewhere.

## Deployment

The GitHub Actions workflow is:

`.github/workflows/deploy-rental-finder.yml`

Manual dispatch:

```bash
gh workflow run deploy-rental-finder.yml \
  --repo benlagrone/fortress-phronesis \
  -f environment=prod
```

The workflow uploads the locked compose file, the remote deployment script, and a short-lived OAuth env file. The remote script:

1. Confirms the private Fortress Rental Finder is reachable over the existing private route.
2. Starts the loopback-only OAuth gateway.
3. Installs a fail-closed HTTP bootstrap.
4. Requires the hostname to resolve to `89.117.151.145`.
5. Obtains a webroot certificate with Certbot.
6. Installs the authenticated Nginx route.
7. Verifies unauthenticated UI and API requests redirect to OAuth instead of reaching Fortress.

## Security boundary

- Only `/oauth2/*` is reachable without an authenticated session, because it implements login and callback handling.
- The public edge never exposes another Fortress path.
- Google access tokens and browser-supplied authorization headers are not forwarded to Fortress.
- Nginx replaces authenticated-user headers with values returned by the loopback OAuth gateway.
- A backend, DNS, OAuth, TLS, or Nginx failure stops activation rather than opening an unauthenticated route.

## Verification

Before login:

```bash
curl -sS -o /dev/null -D - https://rentalfinder.lecrownproperties.com/
curl -sS -o /dev/null -D - https://rentalfinder.lecrownproperties.com/rental-finder/api/listings/search
```

Both must return `302` with a location under `/oauth2/start`.

Browser verification must then confirm:

1. A LeCrown Workspace account can sign in and load Rental Finder.
2. A non-LeCrown Google account is rejected.
3. Rental and Land Finder API calls work after authentication.
4. Signing out removes access and the next request returns to Google sign-in.

## Rollback

Disable the public edge without changing the private Rental Finder:

```bash
rm -f /etc/nginx/sites-enabled/rentalfinder.lecrownproperties.com
nginx -t
systemctl reload nginx
docker compose --env-file /opt/rental-finder/env/google-oauth.prod.env \
  -p rental-finder-edge \
  -f /opt/rental-finder/deploy/docker-compose.rental-finder.yml down
```

The LAN URLs remain unchanged throughout rollout and rollback.
