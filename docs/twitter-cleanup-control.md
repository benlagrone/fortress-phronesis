# X/Twitter Persona Control - Fortress LAN Surface

This document records the private Fortress LAN runtime surface for the
`twitterApi` persona control pane. The service supports local operator review of
X/Twitter archive sentiment, engagement, deletion queues, cleanup history,
marketing queue state, randomized scheduler decisions, profile rules, and persona
strategy.

## Ownership

- Source project: `/Users/benjaminlagrone/Documents/projects/twitterApi`
- Fortress LAN control-plane project: `/Users/benjaminlagrone/Documents/projects/fortress-lan`
- Service id: `twitter-cleanup-control` (legacy id; branded as Persona Control)
- Docker profile: `twitter-cleanup`
- Default host port: `8765`

## Privacy Boundary

This surface contains private social archive analysis, deletion state, marketing queue state, and scheduler decisions. Keep it
LAN/private-route only. Do not expose it through public nginx, public DNS,
Contabo public ports, or unauthenticated deletion endpoints.

The control pane is read-only today. Any future destructive deletion, posting,
or scheduling execution controls must remain explicit, authenticated, and
operator-local.

## Runtime Shape

The `twitterApi` image builds from its project-local `Dockerfile`. The image does
not bake the archive, `.env`, or output state into the image. Runtime data is
mounted by Fortress LAN Compose:

```text
TWITTER_CLEANUP_SOURCE_DIR=/home/master-benjamin/Projects/twitterApi
TWITTER_CLEANUP_ARCHIVE_DIR=/home/master-benjamin/Projects/twitterApi/archive
TWITTER_CLEANUP_OUTPUT_DIR=/home/master-benjamin/Projects/twitterApi/output
TWITTER_CLEANUP_CONFIG=/home/master-benjamin/Projects/twitterApi/cleanup_control.json
TWITTER_PERSONA_CONFIG=/home/master-benjamin/Projects/twitterApi/persona_lab.json
TWITTER_CLEANUP_CONTROL_PORT=8765
TWITTER_CLEANUP_ENABLE_SERVICE=true
```

Control-plane URLs:

```text
http://fortress.local/twitter-cleanup
http://fortress.lan/twitter-cleanup
```

Dedicated service URLs:

```text
http://twitter-cleanup.fortress.local/
http://twitter-cleanup.fortress.lan:8765/
http://192.168.0.126:8765/
```

Health/status:

```text
GET /healthz
GET /api/status
```

## Deploy Command

Deploy only this service from the Fortress LAN deploy root:

```bash
cd /home/master-benjamin/Projects/fortress-lan
TWITTER_CLEANUP_ENABLE_SERVICE=true \
  bash scripts/deploy-fortress-lan.sh --service twitter-cleanup-control
```

Do not use broad `docker compose up` commands for this change. Follow
`fortress-lan/docs/deploy-law.md`.

## Preflight

Before deploying, confirm the Fortress LAN host has the source project and data:

```bash
test -f /home/master-benjamin/Projects/twitterApi/Dockerfile
test -f /home/master-benjamin/Projects/twitterApi/cleanup_control.json
test -f /home/master-benjamin/Projects/twitterApi/persona_lab.json
test -d /home/master-benjamin/Projects/twitterApi/archive
test -d /home/master-benjamin/Projects/twitterApi/output
```

## Verification

```bash
curl -fsS http://127.0.0.1:8765/healthz
curl -fsS http://127.0.0.1:8765/api/status
curl -fsS http://192.168.0.126:8765/healthz
```

Then open:

```text
http://fortress.lan/twitter-cleanup
```
