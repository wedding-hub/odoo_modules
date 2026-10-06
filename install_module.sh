#!/usr/bin/env bash
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

DB_NAME="${1:-odoo20}"

echo "=================================================="
echo "Installing/Updating account_enterprise_ce in DB: $DB_NAME"
echo "=================================================="

# Run odoo update in container
docker compose exec web odoo -d "$DB_NAME" -u account_enterprise_ce --stop-after-init || \
docker compose exec web odoo -d "$DB_NAME" -i account_enterprise_ce --stop-after-init

echo ""
echo "Restarting Odoo web service to reload assets..."
docker compose restart web

echo "✅ Module account_enterprise_ce installed/updated!"
echo "➡️  Open: http://localhost:8070"
