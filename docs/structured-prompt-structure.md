You are an expert in system architecture visualization.
Generate a **Mermaid graph TD diagram** that shows the complete internal structure of the application or server described below. 
Match the style and depth of this example pattern:
- Explicitly label each entrypoint (public domain, API, auth server)
- Show every major directory as a `subgraph`
- Include internal files or components as nodes inside each subgraph
- Use directed edges (→) to illustrate routing, proxy, and data dependencies
- Include connection arrows between folders, services, and logical flows
- Add comments like "%% ─── SECTION ───" to organize the diagram
- Keep layout compact but exhaustive, listing every file or endpoint known

Output should **exactly** match the structure and level of detail seen in this sample pattern:

graph TD

%% ─── ENTRYPOINTS ─────────────────────────────
A1["🌐 pericopeai.com (Public Entry)"]
A2["🔐 auth.pericopeai.com (Keycloak Realm)"]
A3["📦 api.pericopeai.com (FastAPI Backend)"]

%% ─── NGINX CONFIGURATION ─────────────────────
subgraph S1["🧭 /etc/nginx/"]
  S1a["sites-available/pericopeai.conf → routing rules"]
  S1b["ssl/ → certificates"]
end

A1 -->|Serves static files| S1a
A3 -->|Reverse proxy target| S1a
A2 -->|Upstream OIDC authority| S1a

%% ─── FRONTEND ────────────────────────────────
subgraph S2["🎨 /var/www/pericopeai/"]
  S2a["build/ → compiled React app"]
  S2b["assets/ → images, fonts, JS bundles"]
  S2c["config.json → Keycloak + API endpoints"]
end

S1a -->|location /| S2a
S2a -->|fetches config + calls /api| A3

%% ─── BACKEND ─────────────────────────────────
subgraph S3["⚙️ /srv/pericopeai/backend/"]
  S3a["main.py → FastAPI entrypoint"]
  S3b["routes/auth.py → Token exchange logic"]
  S3c["routes/chat.py → Chat + RAG endpoints"]
  S3d["utils/token_handler.py → Validate + refresh JWTs"]
  S3e["db/models.py → ORM models for users/messages"]
  S3f[".env → Secrets, DB creds, OIDC client vars"]
  S3g["/logs/ → uvicorn + audit logs"]
end

S2a -->|/api/chat, /api/memory| S3c
S2a -->|/auth/exchange| S3b
S3b -->|POST /token| A2
S3a -->|reads config + mounts routers| S3b & S3c
S3d --> S3a
S3a -->|uses SQLAlchemy| S3e
S3a -->|logs events| S3g

%% ─── DATABASE ────────────────────────────────
subgraph S4["🗄️ /var/lib/mysql/"]
  S4a["users"]
  S4b["sessions"]
  S4c["messages"]
  S4d["persona_configs"]
end

S3e -->|ORM bind| S4
S3b -->|store session| S4b
S3c -->|store messages| S4c

%% ─── AUTH SERVER ─────────────────────────────
subgraph S5["🔐 /opt/keycloak/"]
  S5a["/data/realms/pericope.json → realm config"]
  S5b["/themes/pericope/ → custom login UI"]
  S5c["/standalone/configuration/ → keycloak.conf"]
end

S3b -->|token exchange| S5a
S2a -->|redirects login| S5a
S5a -->|returns tokens| S3b

%% ─── LOGICAL FLOW ────────────────────────────
A1 -->|login redirect| A2
A2 -->|authorization code| A1
A1 -->|token exchange| A3
A3 -->|authenticate + persist| S4
A3 -->|serve responses| A1

---

Now replace all components, folders, and flows below with your own system details and use the **same hierarchical depth** and formatting:

System name: {{system_name}}
Entrypoints: {{entrypoints (domain or endpoints)}}
Frontend stack: {{frontend_framework + path}}
Backend stack: {{backend_framework + path}}
Auth provider: {{auth_system + realm + files}}
Database: {{db_system + structure + data directories}}
Config paths: {{config_files}}
Flow summary: {{user_flow (end-to-end)}}