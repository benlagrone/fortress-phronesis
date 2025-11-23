# ASKMORTGAGEAUTHORITY + PERICOPEAI — INFRASTRUCTURE & APPLICATION HANDBACK

Prepared for: Master Benjamin  
Environment: Contabo VPS + HostGator Shared Hosting  
Date: Most recent verification log included

---

## 1) Executive Summary

You operate a hybrid multi-domain, multi-application environment:
- Contabo VPS hosts PericopeAI, AskMortgageAuthority WordPress, AMA Chat API, Keycloak, MariaDB, Nginx, and Apache (PHP). Nginx terminates HTTPS on 80/443 and proxies Apache on 8080 for WordPress.
- HostGator shared hosting serves AMA CRM API, Mortgage Calculators, LeCrown sites, and EnergyDataExplorer.
- Two FastAPI servers, two Keycloak runtimes, and conflicting Nginx server blocks exist today.

This handback captures the live system state from diagnostics and defines boundaries for safe containerization and deployment.

---

## 2) Confirmed DNS Map (Authoritative)

Contabo (89.117.151.145)
- pericopeai.com — PericopeAI frontend
- auth.pericopeai.com — PericopeAI Keycloak
- askmortgageauthority.com — AMA WordPress
- chat.askmortgageauthority.com — AMA Chat API

HostGator (50.6.160.246)
- calculator.askmortgageauthority.com — Mortgage Calculator
- lecrownproperties.com — Business site
- lecrownhomes.com — Business site
- lecrowndevelopment.com — Business site
- energydataexplorer.com — Business site
- api.energydataexplorer.com — API

Missing / unconfigured
- crm.askmortgageauthority.com — should point to HostGator
- auth.askmortgageauthority.com — should point to Contabo
- api.pericopeai.com — optional (path routing used)
- calculators.askmortgageauthority.com — unused

---

## 3) Contabo Services (Live State)

Nginx (active)
- Primary public web server; HTTPS termination.
- Proxies to Apache:8080 (WordPress), PericopeAI FastAPI 127.0.0.1:8000, AMA Chat API 127.0.0.1:9001, Keycloak (host or container).
- Logs show conflicting server blocks for AMA; duplicate configs exist.

Apache (active)
- Handles WordPress PHP; bound to port 8080; Nginx proxies to it.

FastAPI services (non-containerized)
- PericopeAI API: /var/www/pericopeai.com/AugustineService/main.py on 8000 (root).
- AMA Chat API: /var/www/chat-api/app/main.py on 9001 (user augustine).

Keycloak
- Host Java process (Quarkus) on 8080.
- Docker container quay.io/keycloak:26 on 8081.
- Two Keycloaks are running simultaneously; one must be retired after audit.

MariaDB (local)
- Listening on 127.0.0.1:3306.
- AMA WordPress uses this DB (DB_HOST=localhost); database name `wordpress` with WooCommerce tables present.
- No other databases present in MariaDB today.
- Chat API and PericopeAI have .env files present but DB hosts/names not yet surfaced; need to read those .env files to confirm targets.

---

## 4) HostGator Services (External)

- AMA CRM API (Laravel) — handles calculator and WP form submissions; uses HostGator MySQL.
- AMA Calculator — static JS HTML.
- HostGator MySQL — CRM leads, calculator submissions, possibly chat sessions.

---

## 5) Key Problems to Fix (in order)

1) Nginx vhost conflicts  
   - Multiple overlapping configs for askmortgageauthority.com, pericopeai.com, Keycloak, chat.askmortgageauthority.com. Error: conflicting server name "askmortgageauthority.com". Result: AMA Chat can be routed to WordPress 404.

2) AMA Chat API reverse proxy broken  
   - 127.0.0.1:9001 works; https://askmortgageauthority.com/chat hits WordPress 404. Cause: AMA vhost overrides Chat API vhost due to duplicate server_name blocks.

3) Two Keycloaks running  
   - Host vs Docker. Choose one, retire the other, adjust proxy.

4) Database structure unclear  
   - AMA WordPress uses Contabo MariaDB, not HostGator. Impacts backups, security, performance, and container migration. Confirm Chat API and PericopeAI DB hosts.

---

## 6) Verified File Locations

- WordPress: /var/www/askmortgageauthority/wp-config.php
- PericopeAI backend: /var/www/pericopeai.com/AugustineService/main.py
- AMA Chat API: /var/www/chat-api/app/main.py
- Keycloak: /opt/keycloak and Docker container auth-keycloak-1
- PericopeAI vhost: present in nginx sites (content not yet dumped)

---

## 7) Scripts Already Run

The verification script covered: Apache status, Nginx status, ports, Docker containers, WordPress directories, PericopeAI directories, AMA Chat API paths, Keycloak processes/ports, SSL certs, reverse proxy behavior, HostGator CRM connectivity. Output was interpreted into this handback.

---

## 8) Next Commands to Run (on Contabo)

Dump configs and env to allow vhost unification and Chat fix:
- sudo cat /etc/nginx/sites-enabled/askmortgageauthority.com
- sudo cat /etc/nginx/sites-enabled/chat.askmortgageauthority.com
- sudo cat /etc/nginx/sites-enabled/pericopeai.com
- sudo cat /etc/nginx/sites-enabled/auth.pericopeai.com.conf
- sudo cat /var/www/chat-api/app/.env   # redact secrets if sharing
- grep DB_NAME /var/www/askmortgageauthority/wp-config.php

---

## 9) Immediate Actions for the Next Engineer

1) Unify Nginx configurations  
   - Remove duplicate server_name blocks; ensure AMA Chat vhost is not overridden; route /chat and /api correctly; upstreams: 8000, 9001, 8080.

2) Decide Keycloak source of truth  
   - Choose host-installed or Docker-installed; remove the duplicate; update reverse proxy.

3) Rationalize DB usage  
   - Separate AMA WordPress DB from PericopeAI; confirm AMA Chat API DB host; keep HostGator CRM DB external.

4) Plan containers  
   - Containerize FastAPI services; containerize Keycloak or retire Docker KC; leave Apache WordPress on host; keep CRM external unless migrating later.

5) Clean folder structure  
   - Move PericopeAI backend to a standard path (/srv or /opt).

6) Re-test routing after unification  
   - AMA homepage, AMA chat, PericopeAI frontend, PericopeAI API, Keycloak login flows, CRM callbacks.

---

## 10) End of Handback

This reflects the current verified state. Future work should start with:
1) Unifying Nginx vhosts  
2) Removing duplicate Keycloak  
3) Normalizing DB connections  
4) Refactoring folder structures  
5) Containerizing only after stability

Optional deliverables: one-page exec summary, detailed migration plan, clean Nginx config pack, containerization blueprint, network diagram (Mermaid), database architecture map.
