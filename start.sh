#!/usr/bin/env bash
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

echo "=================================================="
echo "Starting Odoo 20 & PostgreSQL with Docker Compose"
echo "=================================================="

docker compose up -d

echo ""
echo "✅ Services are running!"
echo "➡️  Open your browser at: http://localhost:8069"
echo "➡️  PostgreSQL is accessible on host port 5433 (user: odoo, password: odoo)"
echo "➡️  To view logs: docker compose logs -f web"
