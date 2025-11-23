You are a system architecture visualization expert.

Generate a **Mermaid graph TD diagram** describing the full internal workings of an application server with these specifications:

App/Server Name: {{app_name}}
Environment: {{infra_provider}} (e.g. Contabo, AWS EC2, etc.)
Architecture Type: {{architecture_style}} (e.g. Docker microservices, VM stack)
Primary Tech Stack:
  - Frontend: {{frontend_stack}}
  - Backend: {{backend_stack}}
  - Authentication: {{auth_system}}
  - Database: {{database_system}}
  - Optional Services: {{cache_system}}, {{message_bus}}
Runtime Processes:
  - {{runtime_processes}} (e.g., nginx, uvicorn, mariadb, keycloak)
Networking / Ports:
  - {{ports}} (JSON of container:port)
Folder Mapping (show in diagram):
  - {{folders}} (JSON: path → purpose)
Data Flow Summary:
  - {{data_flow}} (e.g. user → nginx → backend → db → auth → user)
Inter-Service Connections:
  - {{connections}} (explicitly list routes and bridges)

Output Requirements:
1. Render a **Mermaid MMD graph TD** with the following sections:
   - USER TRAFFIC (entry from browser)
   - NGINX / REVERSE PROXY CONTAINER (list exact port bindings and config files)
   - FRONTEND (show paths like build, assets, config.json)
   - BACKEND (show internal scripts, utils, .env, logs)
   - DATABASE (show data directories and table roles)
   - AUTHENTICATION SERVER (show realm configs, theme, ports)
   - NETWORKING (show docker network bridges and directionality)
   - FOLDER SUMMARY NODES (explicit mapping of folder → function)
2. Label every subgraph with:
   - Folder path  
   - Role description  
   - Port (if applicable)
3. Include **directional arrows** to indicate network or dependency flow (→).
4. Annotate nodes with comments explaining what each process/file does.
5. Use emoji labels for clarity:
   - 🌐 Frontend  
   - ⚙️ Backend  
   - 🔐 Auth  
   - 🧭 Proxy  
   - 🗄️ Database  
   - 🕸️ Network  
   - 📂 Folder Summary
6. Ensure the result follows the structural depth of this pattern: