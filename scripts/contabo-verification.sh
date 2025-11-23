#!/usr/bin/env bash
# Read-only diagnostics for the Contabo server. Runs service/process, port, file
# location, DB, proxy, and SSL checks. Safe to run; no changes are made.

set -euo pipefail

section() {
  printf "\n=== %s ===\n" "$1"
}

section "Apache Status"
sudo systemctl status apache2 --no-pager || echo "apache missing"

section "Nginx Status"
sudo systemctl status nginx --no-pager || echo "nginx missing"

section "Ports Listening"
sudo lsof -iTCP -sTCP:LISTEN -nP || true

section "Docker Containers"
docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Ports}}\t{{.Status}}" || true

section "Search for WordPress Directories"
sudo find /var/www /srv /home -maxdepth 3 -type f -name "wp-config.php" 2>/dev/null || true

section "Search for PericopeAI Backend"
sudo find /srv /opt /var -maxdepth 4 -type f -name "main.py" 2>/dev/null | grep -i pericope || true

section "Keycloak Process Check"
ps aux | grep -i keycloak | grep -v grep || true
section "Keycloak Ports"
sudo lsof -iTCP -sTCP:LISTEN -nP | grep -E "8080|8443|keycloak" || true

section "Search for AMA Chat API"
sudo find /srv /var /opt -maxdepth 4 -type f -name "main.py" 2>/dev/null | grep -i chat || true
section "HTTP Test AMA Chat API (localhost:8000)"
curl -I http://127.0.0.1:8000 2>/dev/null || echo "No response on 8000"
section "HTTP Test AMA Chat API (domain)"
curl -I https://askmortgageauthority.com/chat 2>/dev/null || true

section "Test CRM HostGator API"
curl -I https://calculator.askmortgageauthority.com 2>/dev/null || true
curl -I https://your-hostgator-crm-domain 2>/dev/null || true

section "MariaDB Service"
sudo systemctl status mariadb --no-pager || echo "MariaDB not installed"
section "MariaDB Ports"
sudo lsof -iTCP:3306 -sTCP:LISTEN -nP || echo "No MySQL on local server"
section "AMA WordPress DB Hosts"
grep -i "DB_HOST" /var/www/*/wp-config.php 2>/dev/null || true
section "AMA Chat API DB Hosts"
grep -R "DB_HOST" /srv/chat_api/* 2>/dev/null || true

section "Nginx Sites Available"
sudo ls -1 /etc/nginx/sites-available/ || true
section "Nginx Sites Enabled"
sudo ls -1 /etc/nginx/sites-enabled/ || true
section "PericopeAI vhost"
sudo cat /etc/nginx/sites-available/pericopeai.conf 2>/dev/null || true
section "AMA vhost"
sudo cat /etc/nginx/sites-available/askmortgageauthority.conf 2>/dev/null || true

section "SSL for pericopeai.com"
echo | openssl s_client -connect pericopeai.com:443 -servername pericopeai.com 2>/dev/null | openssl x509 -noout -subject -issuer -dates || true
section "SSL for askmortgageauthority.com"
echo | openssl s_client -connect askmortgageauthority.com:443 -servername askmortgageauthority.com 2>/dev/null | openssl x509 -noout -subject -issuer -dates || true
section "SSL for chat.askmortgageauthority.com"
echo | openssl s_client -connect chat.askmortgageauthority.com:443 -servername chat.askmortgageauthority.com 2>/dev/null | openssl x509 -noout -subject -issuer -dates || true

section "Reverse Proxy Checks"
curl -I https://askmortgageauthority.com --max-time 5 || true
curl -I https://askmortgageauthority.com/chat --max-time 5 || true
curl -I https://pericopeai.com/api --max-time 5 || true

section "Public DNS (run on your Mac, not server)"
cat <<'EOF'
domains=(
pericopeai.com
auth.pericopeai.com
askmortgageauthority.com
chat.askmortgageauthority.com
calculator.askmortgageauthority.com
lecrownproperties.com
lecrownhomes.com
lecrowndevelopment.com
energydataexplorer.com
api.energydataexplorer.com
)
for d in "${domains[@]}"; do
  echo "===== $d ====="
  dig +short "$d"
done
EOF
