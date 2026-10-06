# Accounting Enterprise (Community Edition) for Odoo 20

Replicates official Odoo Enterprise Accounting (`account_accountant`) functionality for **Odoo 20 Community Edition**.

## Features

1. **Top-Level Accounting Navigation & Dashboard**:
   - Rebrands "Invoicing" to "Accounting".
   - Unlocks the native Accounting Journal Dashboard with Bank, Cash, and Invoicing cards.
2. **Inventory Valuation & FIFO GL Audit**:
   - Aggregates `stock.valuation.layer` data.
   - Real-time audit of open and consumed FIFO cost layers.
   - Direct reconciliation of Physical SVL Stock Value against the General Ledger (GL).
   - COGS verification for delivery moves.
3. **Dynamic Financial Reports**:
   - Interactive OWL 2 Client Action for Balance Sheet, Profit & Loss, Trial Balance, General Ledger, and Aged Payables/Receivables.
   - Quick date presets, target move filter, and QWeb PDF printable reports.
4. **Fixed Asset Management**:
   - Straight-Line and Declining Balance (Degressive) depreciation with Prorata Temporis.
   - Asset Models (templates) and automatic draft asset creation from Vendor Bills.
   - Bulk depreciation entry generator with accountant review.

## Installation

See [INSTALL.md](INSTALL.md) for full step-by-step instructions.
