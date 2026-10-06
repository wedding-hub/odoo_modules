# Installation & Setup Guide: Accounting Enterprise (Community Edition)

This guide walks you through installing and configuring the **`account_enterprise_ce`** module on your local Odoo 20 Community Edition instance.

---

## Prerequisites

1. **Odoo 20 Community Edition** running locally.
2. Standard core modules installed in your database:
   - `account` (Invoicing)
   - `stock` (Inventory)
   - `stock_account` (Automatic Inventory Valuation)
   - `analytic` (Analytic Accounting)

---

## Method 1: Installation via Odoo Web UI (Recommended)

### Step 1: Update your Odoo Configuration (`odoo.conf`)
Open your `odoo.conf` file (or configuration file) and add the path to your custom modules folder in the `addons_path` parameter:

```ini
[options]
addons_path = /path/to/your/odoo/addons,/Users/lonhpiseth/odoo_modules
```

> **Note:** Paths are comma-separated without spaces. `/Users/lonhpiseth/odoo_modules` contains the `account_enterprise_ce` folder.

### Step 2: Restart your Odoo Server
Restart your local Odoo service in terminal so it scans the new addons directory:
```bash
# Example if running directly from source:
python3 odoo-bin -c /path/to/odoo.conf
```

### Step 3: Activate Developer Mode
1. Open your browser and log into Odoo as an Administrator.
2. Go to **Settings** (General Settings).
3. Scroll to the bottom and click **Activate the developer mode** (or add `?debug=1` to the URL).

### Step 4: Update the Apps List
1. In the top navigation bar, click the app switcher icon and open **Apps**.
2. In the top menu of the Apps view, click **Update Apps List** (this menu item appears only in Developer Mode).
3. In the pop-up modal, click **Update**.

### Step 5: Install the Module
1. In the search bar of the **Apps** page, **clear the default "Apps" filter** (click the 'x' on the tag).
2. Search for: `account_enterprise_ce` or `Accounting Enterprise`.
3. Locate **Accounting Enterprise (Community Edition)** and click **Install**.

---

## Method 2: Installation via Terminal Command Line

You can also install the module directly from the terminal without using the web UI:

```bash
python3 odoo-bin -c /path/to/odoo.conf \
  --addons-path=/path/to/odoo/addons,/Users/lonhpiseth/odoo_modules \
  -d <your_database_name> \
  -i account_enterprise_ce \
  --stop-after-init
```

Once completed, start your server normally:
```bash
python3 odoo-bin -c /path/to/odoo.conf
```

---

## Post-Installation Verification & User Access

### 1. Verify User Permissions
To ensure you can view all unlocked accounting features:
1. Go to **Settings > Users & Companies > Users**.
2. Select your user account.
3. Under the **Accounting / Invoicing** section, ensure your role is set to:
   - **Billing Administrator** (or ensure **Show Full Accounting Features** is checked if visible in your localization).
4. Save and refresh your browser (`Cmd + Shift + R`).

### 2. Verify New Menus & Dashboard
1. The top navbar now displays **Accounting** instead of "Invoicing".
2. **Accounting > Dashboard** opens the native Accounting Journal Dashboard with Bank, Cash, Customer Invoices, and Vendor Bills kanban cards.

### 3. Test New Features
- **Dynamic Financial Reports**:
  - Go to **Accounting > Reporting**.
  - Click **Balance Sheet**, **Profit and Loss**, **Trial Balance**, **General Ledger**, or **Aged Receivable / Aged Payable**.
  - Test quick date filters (*This Month*, *This Year*), unfold general ledger accounts, and click **PDF** to print.
- **Fixed Asset Management**:
  - Go to **Accounting > Configuration > Asset Models** to view or create asset templates.
  - Go to **Accounting > Accounting > Assets** to view fixed assets and depreciation boards.
- **Inventory Valuation & FIFO Audit**:
  - Go to **Accounting > Reporting > Inventory Valuation & FIFO Audit**.
  - Run the audit wizard to reconcile physical stock layers (`stock.valuation.layer`) against your General Ledger stock valuation accounts.

---

## Troubleshooting

- **Module Not Found in Apps List?**
  - Make sure you removed the default `[Apps]` filter in the search box.
  - Verify that the path `/Users/lonhpiseth/odoo_modules` is present in your `odoo.conf` `addons_path`.
  - Check file permissions: ensure the Odoo user has read access to the directory.
- **Changes Not Appearing after Code Edits?**
  - Run an upgrade command in terminal:
    ```bash
    python3 odoo-bin -c odoo.conf -d <your_db> -u account_enterprise_ce --stop-after-init
    ```
