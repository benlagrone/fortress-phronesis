# Fortress realm example

Prepared import for the Sextant remote edge. This file has no users and no
client secret. Do not import it until the go-live gate in
[docs/sextant-remote.md](../../docs/sextant-remote.md) is open, and do not
import it into the `pericope` realm.

The public issuer is `https://auth.pericopeai.com/realms/fortress`. Two
Keycloak processes have been recorded on the host that serves that name: a
host process and the `auth-keycloak` container. Confirm which one the live
`auth.pericopeai.com` nginx vhost proxies to before running `kcadm`. Use that
instance's loopback admin URL. Do not send the admin credential to the public
hostname, and do not put it on the command line.

## What the example sets

- Realm `fortress`, `registrationAllowed` false, `bruteForceProtected` true.
  Lockout thresholds stay at the server defaults.
- `CONFIGURE_TOTP` is a default required action, so the first login must enroll
  an OTP app.
- Browser flow `sextant-browser`: an existing session cookie is accepted;
  otherwise username, password, and OTP are all required.
- Realm role `sextant-operator`.
- Confidential client `sextant-remote`. Standard flow on. Implicit flow,
  direct access grants, and service accounts off. PKCE `S256`. Redirect URI
  `https://sextant.lecrowndevelopment.com/oauth2/callback`. Web origin
  `https://sextant.lecrowndevelopment.com`. Post-logout redirect
  `https://sextant.lecrowndevelopment.com/`. An audience mapper adds
  `sextant-remote` to the token `aud` claim, which oauth2-proxy requires.
- No `secret` field. Keycloak generates the client secret.
- No users. Benjamin chooses the single operator identity at go-live.

## Import

Stop if realm `fortress` already exists. This example is a create, not an
overwrite. Do not partial-import it over a populated realm.

```bash
# On the host that serves auth.pericopeai.com, after the vhost check:
sudo nginx -T | awk '
  /server_name[[:space:]]+auth\.pericopeai\.com/ {capture=1}
  capture {print}
  capture && /^}/ {exit}
'
```

The `proxy_pass` in that server block is the instance to administer. Then,
against that instance only:

```bash
sudo docker exec -it "$KC_CONTAINER" /opt/keycloak/bin/kcadm.sh \
  config credentials \
  --server "$KC_ADMIN_URL" \
  --realm master \
  --user "$KC_ADMIN_USER"
```

`$KC_ADMIN_URL` is the loopback URL of the confirmed instance. The command
prompts for the admin password. Omit `--password`.

Create the realm from this example. The container reads stdin; the file stays
on the host:

```bash
sudo docker exec -i "$KC_CONTAINER" /opt/keycloak/bin/kcadm.sh create realms -f - \
  < deploy/keycloak/fortress-realm.example.json
```

If the host process is the one behind the vhost, run that same `kcadm.sh`
from the host Keycloak install instead of `docker exec`. Do not run both.

## Check the realm before creating a user

```bash
sudo docker exec "$KC_CONTAINER" /opt/keycloak/bin/kcadm.sh get realms/fortress \
  --fields realm,registrationAllowed,bruteForceProtected,browserFlow
sudo docker exec "$KC_CONTAINER" /opt/keycloak/bin/kcadm.sh get \
  authentication/required-actions/CONFIGURE_TOTP -r fortress
sudo docker exec "$KC_CONTAINER" /opt/keycloak/bin/kcadm.sh get clients -r fortress \
  -q clientId=sextant-remote \
  --fields id,clientId,publicClient,standardFlowEnabled,implicitFlowEnabled,directAccessGrantsEnabled,serviceAccountsEnabled
sudo docker exec "$KC_CONTAINER" /opt/keycloak/bin/kcadm.sh get roles -r fortress \
  --fields name
```

Expect `registrationAllowed` false, `bruteForceProtected` true,
`browserFlow` `sextant-browser`, and `CONFIGURE_TOTP` with `defaultAction`
true. Expect client flags matching the list above. Keycloak also creates its
own default roles (`default-roles-fortress`, and usually `offline_access` and
`uma_authorization`). Confirm the client still has the built-in `roles`
client scope so `realm_access.roles` contains `sextant-operator`. The token
endpoint's client evaluation screen is the check. Do not print a token into
a ticket or into git.

## One operator

The username and email are chosen by Benjamin and are not in git. Set them
only in the operator's shell, not in this repository.

```bash
sudo docker exec -i "$KC_CONTAINER" /opt/keycloak/bin/kcadm.sh create users -r fortress \
  -s username="$SEXTANT_OPERATOR_USERNAME" \
  -s email="$SEXTANT_OPERATOR_EMAIL" \
  -s enabled=true \
  -s emailVerified=true

sudo docker exec -it "$KC_CONTAINER" /opt/keycloak/bin/kcadm.sh set-password \
  -r fortress \
  --username "$SEXTANT_OPERATOR_USERNAME"

sudo docker exec "$KC_CONTAINER" /opt/keycloak/bin/kcadm.sh add-roles \
  -r fortress \
  --uusername "$SEXTANT_OPERATOR_USERNAME" \
  --rolename sextant-operator
```

`set-password` prompts. The first browser login must enroll OTP because
`CONFIGURE_TOTP` is a default required action.

## Store the generated client secret

Keycloak generates the secret. FortressPhronesis stores it in
`/etc/fortress/sextant-remote-edge.env` (root:root, mode 0600), outside this
repo. The snippet below writes the file and prints only `stored
OAUTH2_PROXY_CLIENT_SECRET`. Do not `echo` the secret, do not `tee` it to a
terminal, and do not paste it into a ticket.

```bash
client_uuid="$(sudo docker exec "$KC_CONTAINER" /opt/keycloak/bin/kcadm.sh \
  get clients -r fortress -q clientId=sextant-remote --fields id \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)[0]["id"])')"

sudo docker exec "$KC_CONTAINER" /opt/keycloak/bin/kcadm.sh \
  get "clients/${client_uuid}/client-secret" -r fortress \
| sudo python3 -c '
import json, pathlib, sys
secret = json.load(sys.stdin)["value"]
if not secret or any(ch.isspace() for ch in secret):
    sys.exit("refusing to store a secret that is not a single line")
path = pathlib.Path("/etc/fortress/sextant-remote-edge.env")
lines = []
if path.exists():
    lines = [ln for ln in path.read_text().splitlines()
             if not ln.startswith("OAUTH2_PROXY_CLIENT_SECRET=")]
lines.append("OAUTH2_PROXY_CLIENT_SECRET=" + secret)
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text("\n".join(lines) + "\n")
path.chmod(0o600)
print("stored OAUTH2_PROXY_CLIENT_SECRET")
'
```

Generate the cookie secret the same way, from `openssl rand -base64 32`, and
store it as `OAUTH2_PROXY_COOKIE_SECRET` with the same rule: single line, mode
0600, no terminal echo. Then recreate the edge container so it reads the file:

```bash
sudo docker compose -p sextant-remote-edge -f docker-compose.sextant-remote-edge.yml up -d
```

## Rollback of this realm

Prefer disabling the client over deleting the realm:

```bash
sudo docker exec "$KC_CONTAINER" /opt/keycloak/bin/kcadm.sh update \
  "clients/${client_uuid}" -r fortress -s enabled=false
```

Delete the realm only when Benjamin says it has no other use.
