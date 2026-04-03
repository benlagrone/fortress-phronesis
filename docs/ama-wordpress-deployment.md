# AMA WordPress Deployment Contract

This file defines the fortress-side deployment contract for
`askmortgageauthority.com` when it is served from the containerized WordPress
stack.

Unlike the GHCR image deploys in this repo, the WordPress publish path is a
backup-first source update on the target host. The source repo carries the
custom runtime overlay, Dockerfile, and plugin install manifest, while
WordPress core comes from the upstream base image during the host build and
uploads stay on persistent host storage.

## Runtime Contract

- Compose file: `docker-compose.wordpress.yml`
- Compose project: `ama-wordpress`
- Services:
  - `wordpress`
  - `nginx`
- Host bind: `127.0.0.1:18020`
- Host Nginx upstream: `http://127.0.0.1:18020`
- Public host: `https://askmortgageauthority.com/`
- Source repo path: `/root/workspace/askmortgageauthority.com`
- WordPress image build source: `${AMA_WORDPRESS_ROOT}/Dockerfile`
- Base image: `wordpress:6.6-php8.3-fpm`

The source repo should contain the low-transport WordPress overlay and runtime
inputs used by the build/deploy flow:

- `.env`
- `Dockerfile`
- `plugins.txt`
- `scripts/install-plugins.sh`
- `nginx/default.conf`
- `custom/wp-content/themes/*`
- `custom/wp-content/plugins/*`
- `custom/wp-content/mu-plugins/*`
- `data/uploads/`

Public WordPress.org plugins are reinstalled after the container starts using
`plugins.txt`. Premium or private plugins that cannot be pulled from
WordPress.org belong under `custom/wp-content/plugins`.

Do not store WordPress core or the full legacy `wp-content` tree in the source
repo. Custom integration code belongs in `plugins` or `mu-plugins`. If an
integration needs runtime assets such as Composer `vendor/` output, keep that
output inside the plugin directory so the deploy remains server-light.

Do not change the project name, source path, service names, or host port
without updating this file, the compose file, and the host Nginx configuration
together.

## Backup Contract

Before every update deploy, run:

```bash
bash scripts/backup-ama-wordpress.sh
```

The backup captures:

- a compressed DB dump from `/root/workspace/askmortgageauthority.com/.env`
- `data/uploads`
- the current `.env`
- `wp-config.php` when present
- the current git SHA and working tree status when the source path is a git repo

Default backup output root:

- `/root/workspace/askmortgageauthority.com/backups/`

Each backup lands in a timestamped directory and refreshes the `latest`
symlink.

## Canonical Deploy Commands

From the fortress repo root on the target host:

```bash
SERVICE_REF=main
SOURCE_SHA=
WORDPRESS_ROOT=/root/workspace/askmortgageauthority.com

BACKUP_LABEL="manual-${SERVICE_REF}" \
WORDPRESS_ROOT="${WORDPRESS_ROOT}" \
bash scripts/backup-ama-wordpress.sh

git -C "${WORDPRESS_ROOT}" fetch origin --tags
git -C "${WORDPRESS_ROOT}" checkout "${SERVICE_REF}"
git -C "${WORDPRESS_ROOT}" pull --ff-only origin "${SERVICE_REF}"

if [[ -n "${SOURCE_SHA}" ]]; then
  git -C "${WORDPRESS_ROOT}" checkout "${SOURCE_SHA}"
fi

install -d \
  "${WORDPRESS_ROOT}/custom/wp-content/themes" \
  "${WORDPRESS_ROOT}/custom/wp-content/plugins" \
  "${WORDPRESS_ROOT}/custom/wp-content/mu-plugins" \
  "${WORDPRESS_ROOT}/data/uploads"

AMA_WORDPRESS_ROOT="${WORDPRESS_ROOT}" \
docker compose -p ama-wordpress -f docker-compose.wordpress.yml pull nginx

AMA_WORDPRESS_ROOT="${WORDPRESS_ROOT}" \
docker compose -p ama-wordpress -f docker-compose.wordpress.yml build wordpress

AMA_WORDPRESS_ROOT="${WORDPRESS_ROOT}" \
docker compose -p ama-wordpress -f docker-compose.wordpress.yml up -d wordpress nginx

AMA_WORDPRESS_ROOT="${WORDPRESS_ROOT}" \
COMPOSE_FILE_PATH="$(pwd)/docker-compose.wordpress.yml" \
COMPOSE_PROJECT_NAME="ama-wordpress" \
bash "${WORDPRESS_ROOT}/scripts/install-plugins.sh"

AMA_WORDPRESS_ROOT="${WORDPRESS_ROOT}" \
docker compose -p ama-wordpress -f docker-compose.wordpress.yml ps wordpress nginx
```

Assumptions:

- `/root/workspace/askmortgageauthority.com` already exists on the server
- that checkout already has a valid `origin` remote
- `.env` in that repo points at the live WordPress database
- `WORDPRESS_CONFIG_EXTRA` in `.env` is the preferred place for custom WordPress
  constants and integration secrets

## GitHub Actions Control Plane

Fortress workflow:

- `.github/workflows/deploy-ama-wordpress.yml`

Expected production secrets:

- `AMA_WORDPRESS_DEPLOY_HOST`
- `AMA_WORDPRESS_DEPLOY_USER`
- `AMA_WORDPRESS_DEPLOY_ROOT`
- `AMA_WORDPRESS_DEPLOY_SSH_KEY`
- `AMA_WORDPRESS_DEPLOY_KNOWN_HOSTS`

Workflow inputs:

- `service_ref` for the source branch to deploy
- optional `source_sha` for an exact pinned commit

The workflow logs into the host, updates the fortress checkout, runs the backup
script, updates the WordPress source checkout, rebuilds the custom WordPress
image from the source repo, reinstalls public plugins from `plugins.txt`,
restarts the WordPress containers, and then runs local plus public smoke
checks.

## Host Nginx

Host Nginx should proxy the public site to:

- `http://127.0.0.1:18020`

Keep TLS termination on host Nginx.

## Verification

Local checks on the host:

```bash
curl -fsSL http://127.0.0.1:18020/ >/dev/null
curl -fsSL http://127.0.0.1:18020/wp-login.php >/dev/null
docker compose -p ama-wordpress -f docker-compose.wordpress.yml ps
```

Public checks:

```bash
curl -fsSL https://askmortgageauthority.com/ >/dev/null
curl -fsSL https://askmortgageauthority.com/wp-login.php >/dev/null
```

## Rollback

Rollback means restoring the most recent green backup, checking out the previous
known-good source SHA, and restarting the same compose project.

Minimum rollback data is already captured by `scripts/backup-ama-wordpress.sh`:

- `db.sql.gz`
- `uploads.tar.gz`
- `.env`
- `wp-config.php` when present
- `git-head.txt`

Use the backup directory from `backups/latest` or a specific timestamped
directory, restore the DB and uploads, then redeploy the prior source SHA
with:

```bash
AMA_WORDPRESS_ROOT="${WORDPRESS_ROOT}" \
docker compose -p ama-wordpress -f docker-compose.wordpress.yml up -d wordpress nginx
```
