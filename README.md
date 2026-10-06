# Odoo 20 Community Docker Environment with Enterprise Accounting

This repository contains:
1. **`account_enterprise_ce`**: The custom Odoo 20 module unlocking Enterprise Accounting features (Dynamic Financial Reports in OWL 2, Fixed Assets, Inventory Valuation & FIFO GL Reconciliation, etc.).
2. **Docker Compose Setup**: Complete, ready-to-run container environment for Odoo 20 and PostgreSQL.

---

## Quick Start (Docker)

### 1. Start Odoo 20 & PostgreSQL
The containers are already configured and running. To control them:
```bash
./start.sh
```
- **Odoo 19 Web Interface**: [http://localhost:8069](http://localhost:8069)
- **PostgreSQL**: Accessible on host port `5433` (user: `odoo`, password: `odoo`)
- **Master Database Password**: `admin` (configured in `config/odoo.conf`)

### 2. Create Your Database
1. Open your browser at [http://localhost:8069](http://localhost:8069).
2. Fill in the database creation form:
   - **Database Name**: e.g., `odoo19`
   - **Email**: admin email (e.g., `admin`)
   - **Password**: admin password (e.g., `admin`)
   - Check **Demo data** (optional, recommended for testing)
3. Click **Create Database**.

### 3. Install the Custom Module

#### Option A: One-Command CLI Install (Fastest)
Once your database is created in the web UI, run:
```bash
./install_module.sh odoo19
```
*(Replace `odoo19` with your database name if different).*
This will install `account_enterprise_ce` and all dependencies (`account`, `stock_account`, `analytic`, etc.) and reload the web container.

#### Option B: Via Odoo Web Interface
1. In Odoo, go to **Settings** and scroll down to click **Activate the developer mode**.
2. Go to **Apps > Update Apps List** and click **Update**.
3. In the search box, **remove the default `Apps` filter**.
4. Search for `account_enterprise_ce` or `Accounting Enterprise`.
5. Click **Install**.

---

## Useful Docker Commands

```bash
# View live logs
docker compose logs -f web

# Stop containers
./stop.sh

# Restart containers
./start.sh
```
