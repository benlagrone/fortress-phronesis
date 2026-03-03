# System Handbook (Verified State)

## Hosting Split
- **Contabo (89.117.151.145):** askmortgageauthority.com (WordPress on Apache 8080), chat.askmortgageauthority.com (FastAPI host process 9001), pericopeai.com (React + FastAPI path /api), auth.pericopeai.com (Keycloak), Nginx 80/443, MariaDB local.
- **HostGator (50.6.160.246):** calculator.askmortgageauthority.com, CRM API (Laravel), LeCrown domains, EnergyDataExplorer, HostGator MySQL for CRM/calculators.

## Key Services on Contabo
- **Nginx:** fronting all Contabo domains; conflicting vhosts for AMA/chat (chat vhost overridden).
- **Apache:** PHP for WordPress on 8080.
- **WordPress:** `/var/www/askmortgageauthority/`; DB_HOST=localhost; DB `wordpress` (WooCommerce tables present).
- **Chat API (host):** `/var/www/chat-api/app/main.py` (FastAPI on 9001); systemd `chat-api.service` runs uvicorn on 127.0.0.1:8000 (keep running).
- **PericopeAI frontend+API (containerized):** `docker-compose.pericope.yml` → pericopeai-api (host port 18000 -> container 8080), pericopeai-frontend (host port 13080 -> container 80). Nginx proxies `/api` to 127.0.0.1:18000 and `/` to 127.0.0.1:13080. `.env` points to HostGator MySQL (`gator4416.hostgator.com`, DB `cwrihote_chatbook`).
- **Keycloak:** two instances — host Java on 8080; Docker `auth-keycloak-1` on 8081 with Postgres DB (kc-db container).
- **MariaDB:** 127.0.0.1:3306; only database present is `wordpress`.

## DNS (Authoritative)
- **Contabo:** pericopeai.com, auth.pericopeai.com, askmortgageauthority.com, chat.askmortgageauthority.com.
- **HostGator:** calculator.askmortgageauthority.com, lecrownproperties.com, lecrownhomes.com, lecrowndevelopment.com, energydataexplorer.com, api.energydataexplorer.com.
- **Missing/unset:** crm.askmortgageauthority.com (should point to HostGator), auth.askmortgageauthority.com (should point to Contabo), api.pericopeai.com (unused; API via /api path).

## Outstanding Issues
- **Nginx conflicts:** Duplicate server_name for askmortgageauthority.com; chat proxy overridden by WordPress vhost.
- **Dual Keycloak:** host vs Docker; choose one and retire the other.
- **Credential hygiene:** PericopeAI .env contains HostGator DB credentials; rotate and store securely. Chat API .env contains provider API keys; rotate if exposed.

## Next Data to Capture
- `/var/www/chat-api/.env` (redact secrets) to confirm DB host/name.
- `/var/www/pericopeai.com/AugustineService/.env` (redact secrets) to confirm DB host/name.
- Active Nginx vhost files for AMA/chat/pericopeai/auth to resolve conflicts.
