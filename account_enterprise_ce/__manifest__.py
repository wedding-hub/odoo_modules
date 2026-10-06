# -*- coding: utf-8 -*-
{
    'name': 'Accounting Enterprise (Community Edition)',
    'version': '20.0.1.0.0',
    'category': 'Accounting/Accounting',
    'summary': 'Unlock and Replicate Enterprise Accounting Features for Odoo 20 Community',
    'description': """
Odoo 20 Accounting Enterprise Replication for Community Edition
===============================================================
This module unlocks official Odoo Enterprise Accounting (account_accountant)
features and adds advanced financial, asset, and inventory audit capabilities for Odoo 20:

Key Features:
-------------
1. Top-Level Accounting Menu & Journal Dashboard
   - Unlocks full Accounting navigation menu structure
   - Unlocks native Accounting Journal Dashboard with actionable KPIs

2. Inventory Valuation & FIFO Cost Layer Auditing
   - Aggregates stock.valuation.layer data as of any selected cut-off date
   - Real-time audit of open and consumed FIFO cost layers
   - Direct reconciliation of Physical SVL Stock Value against the General Ledger (GL)
   - Discrepancy diagnosis (unposted stock moves, manual GL entries, missing accounts)
   - COGS verification to confirm delivery moves have generated matching COGS journal entries
   - Professional QWeb PDF Inventory Valuation & FIFO Audit Report

3. Dynamic Financial Reports (OWL 2 Client Action & PDF)
   - Balance Sheet (Assets = Liabilities + Equity, Current Year Earnings calculation)
   - Profit and Loss (Operating Revenue, COGS, Gross Profit, Operating Expenses, Net Profit)
   - Trial Balance (Initial Balance, Period Debit, Period Credit, Ending Balance)
   - General Ledger (Per-account collapsible breakdown with interactive drilldown into moves)
   - Aged Receivable & Aged Payable (Partner breakdown across 1-30, 31-60, 61-90, 91-120, 120+ days)
   - Interactive date presets, target move filter, and branded PDF printout

4. Fixed Asset Management & Depreciation
   - Straight-Line and Declining Balance (Degressive) methods with Prorata Temporis
   - Asset Models (templates) with pre-configured depreciation rules and accounts
   - Automatic draft asset creation upon posting Vendor Bills
   - Visual depreciation schedule board with cumulative and residual book value tracking
   - Bulk depreciation entry generator with accountant review before posting

5. Upcoming in Steps 3 & 4:
   - Deferred Accounting (Revenue and Expense amortization schedules)
   - 4-Tier Fiscal Period Locking (Sales, Purchase, Non-Adviser, All-Users & Tax)
   - Bank Reconciliation interactive dual-panel widget with CSV/OFX parsers
   - Multi-tier Customer Payment Follow-ups and Analytic Budgeting
    """,
    'author': 'Antigravity / Odoo Expert',
    'website': 'https://www.odoo.com',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'account',
        'stock',
        'stock_account',
        'analytic',
        'mail',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/stock_valuation_fifo_views.xml',
        'views/stock_valuation_fifo_wizard_views.xml',
        'views/account_asset_views.xml',
        'views/financial_report_views.xml',
        'views/menuitems.xml',
        'report/stock_valuation_fifo_report.xml',
        'report/stock_valuation_fifo_template.xml',
        'report/financial_reports_report.xml',
        'report/financial_reports_template.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'account_enterprise_ce/static/src/components/financial_report/financial_report.js',
            'account_enterprise_ce/static/src/components/financial_report/financial_report.xml',
            'account_enterprise_ce/static/src/components/financial_report/financial_report.scss',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
}
