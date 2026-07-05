# Metro LeCrown Certification Tracker Portal Package

This folder contains the Metro LeCrown certification tracker package for the
LeCrown client portal. This package lives in Fortress Phronesis because portal
workspace creation and document upload are operational LeCrown platform work.

Source tracker project:

- `/Users/benjaminlagrone/Documents/projects/metroLecrown`

Portal target:

- Project ID: `metro-lecrown-certification-tracker`
- Project name: `Metro LeCrown Government Certification Tracker`
- Portal URL: `https://lecrowndevelopment.com/portal/login`
- Public API project route:
  `POST https://lecrowndevelopment.com/api/portal/projects`
- Public API document route:
  `POST https://lecrowndevelopment.com/api/portal/projects/:projectId/documents`

## Files

- `payloads/metro-lecrown-certification-tracker-project.json`: project creation
  payload.
- `payloads/metro-lecrown-certification-tracker-documents.json`: document
  upload manifest.
- `scripts/upload_lecrowndev_portal_package.mjs`: authenticated uploader that
  reads the manifest from this Fortress package and reads source files from
  `metroLecrown`.

## Upload Rule

Use the authenticated LeCrown portal API or the LeCrown portal admin UI. Do not
upload sensitive files to a generic workspace. The portal project ID should be
`metro-lecrown-certification-tracker`.

Do not store bearer tokens, passwords, bank values, SSNs, or private download
URLs in this package.

## API Upload

Dry run:

```bash
node scripts/upload_lecrowndev_portal_package.mjs --dry-run
```

Authenticated upload:

```bash
LECROWN_PORTAL_BEARER_TOKEN="$TOKEN" \
  node scripts/upload_lecrowndev_portal_package.mjs
```

Create or verify the portal project without uploading documents:

```bash
LECROWN_PORTAL_BEARER_TOKEN="$TOKEN" \
  node scripts/upload_lecrowndev_portal_package.mjs --skip-documents
```

The default API base is `https://lecrowndevelopment.com/api/portal`. Override it
with `--api-base` for local portal testing.

The default source root is
`/Users/benjaminlagrone/Documents/projects/metroLecrown`. Override it with
`--source-root` only if the tracker project is checked out somewhere else.

## Ownership Boundary

- Fortress Phronesis owns this portal package and the upload operation.
- `metroLecrown` owns the source certification tracker CSVs, markdown files,
  evidence register, and capability statement drafts.
- The LeCrown portal owns authenticated document access once uploaded.
- Do not copy private credentials or raw secrets into this package.
