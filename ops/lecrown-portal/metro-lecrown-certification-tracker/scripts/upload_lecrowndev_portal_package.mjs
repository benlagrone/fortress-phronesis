import { readFile } from "node:fs/promises"
import { basename, dirname, resolve } from "node:path"
import { fileURLToPath } from "node:url"

const defaultApiBase = "https://lecrowndevelopment.com/api/portal"
const packageRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..")
const defaultSourceRoot =
  "/Users/benjaminlagrone/Documents/projects/metroLecrown"
const projectPayloadPath =
  `${packageRoot}/payloads/metro-lecrown-certification-tracker-project.json`
const documentsPayloadPath =
  `${packageRoot}/payloads/metro-lecrown-certification-tracker-documents.json`

function usage() {
  console.log(`Usage:
  LECROWN_PORTAL_BEARER_TOKEN=<token> node scripts/upload_lecrowndev_portal_package.mjs [options]

Options:
  --api-base <url>       Portal API base. Default: ${defaultApiBase}
  --project <path>       Project JSON payload. Default: ${projectPayloadPath}
  --documents <path>     Document manifest JSON. Default: ${documentsPayloadPath}
  --source-root <path>   Source tracker root. Default: ${defaultSourceRoot}
  --skip-documents       Create or verify the project only.
  --dry-run              Print planned project/doc uploads without API writes.
  --help                 Show this help.

The public LeCrown site proxies /api/portal/* to the portal backend.
`)
}

function parseArgs(argv) {
  const options = {
    apiBase: process.env.LECROWN_PORTAL_API_BASE || defaultApiBase,
    documentsPath: documentsPayloadPath,
    dryRun: false,
    projectPath: projectPayloadPath,
    sourceRoot: process.env.METRO_LECROWN_SOURCE_ROOT || defaultSourceRoot,
    skipDocuments: false
  }

  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index]

    if (arg === "--help") {
      options.help = true
      continue
    }

    if (arg === "--dry-run") {
      options.dryRun = true
      continue
    }

    if (arg === "--skip-documents") {
      options.skipDocuments = true
      continue
    }

    if (arg === "--api-base") {
      options.apiBase = argv[index + 1] || ""
      index += 1
      continue
    }

    if (arg === "--project") {
      options.projectPath = argv[index + 1] || ""
      index += 1
      continue
    }

    if (arg === "--documents") {
      options.documentsPath = argv[index + 1] || ""
      index += 1
      continue
    }

    if (arg === "--source-root") {
      options.sourceRoot = argv[index + 1] || ""
      index += 1
      continue
    }

    throw new Error(`Unknown argument: ${arg}`)
  }

  return options
}

async function readJson(path) {
  return JSON.parse(await readFile(path, "utf8"))
}

function normalizeApiBase(apiBase) {
  return String(apiBase || "").replace(/\/+$/, "")
}

async function portalRequest(apiBase, token, path, {
  body,
  method = "GET"
} = {}) {
  const response = await fetch(`${apiBase}${path}`, {
    body: body === undefined ? undefined : JSON.stringify(body),
    headers: {
      Accept: "application/json",
      Authorization: `Bearer ${token}`,
      ...(body === undefined ? {} : { "Content-Type": "application/json" })
    },
    method
  })

  const data = await response.json().catch(() => null)
  if (!response.ok) {
    const message = data?.error || response.statusText || "Portal request failed."
    const error = new Error(`${method} ${path} failed (${response.status}): ${message}`)
    error.status = response.status
    error.data = data
    throw error
  }

  return data
}

async function ensureProject(apiBase, token, project) {
  try {
    const data = await portalRequest(
      apiBase,
      token,
      `/projects/${encodeURIComponent(project.id)}`
    )
    return { created: false, project: data.project }
  } catch (error) {
    if (error.status !== 404) {
      throw error
    }
  }

  const data = await portalRequest(apiBase, token, "/projects", {
    body: project,
    method: "POST"
  })
  return { created: true, project: data.project }
}

async function uploadDocument(apiBase, token, projectId, sourceRoot, entry) {
  const absolutePath = resolve(sourceRoot, entry.localPath)
  const content = await readFile(absolutePath)
  const payload = {
    category: entry.category,
    contentBase64: content.toString("base64"),
    contentType: entry.contentType || "application/octet-stream",
    description: entry.description || "",
    fileName: entry.fileName || basename(entry.localPath),
    id: entry.id,
    name: entry.name
  }

  const data = await portalRequest(
    apiBase,
    token,
    `/projects/${encodeURIComponent(projectId)}/documents`,
    {
      body: payload,
      method: "POST"
    }
  )

  return data.document
}

async function main() {
  const options = parseArgs(process.argv.slice(2))
  if (options.help) {
    usage()
    return
  }

  const apiBase = normalizeApiBase(options.apiBase)
  const project = await readJson(options.projectPath)
  const documents = await readJson(options.documentsPath)

  if (!apiBase) {
    throw new Error("Portal API base is required.")
  }

  if (!project.id) {
    throw new Error("Project payload must include id.")
  }

  if (!Array.isArray(documents)) {
    throw new Error("Document manifest must be a JSON array.")
  }

  if (options.dryRun) {
    console.log(`DRY RUN: project ${project.id} -> ${apiBase}`)
    for (const document of documents) {
      console.log(
        `DRY RUN: document ${document.id} <- ${resolve(options.sourceRoot, document.localPath)}`
      )
    }
    return
  }

  const token = process.env.LECROWN_PORTAL_BEARER_TOKEN
  if (!token) {
    throw new Error("Set LECROWN_PORTAL_BEARER_TOKEN before uploading.")
  }

  const projectResult = await ensureProject(apiBase, token, project)
  console.log(
    `${projectResult.created ? "Created" : "Found"} project: ${projectResult.project.id}`
  )

  if (options.skipDocuments) {
    return
  }

  for (const entry of documents) {
    const uploaded = await uploadDocument(
      apiBase,
      token,
      project.id,
      options.sourceRoot,
      entry
    )
    console.log(`Uploaded document: ${uploaded.id} ${uploaded.name}`)
  }
}

main().catch((error) => {
  console.error(error.message)
  process.exitCode = 1
})
