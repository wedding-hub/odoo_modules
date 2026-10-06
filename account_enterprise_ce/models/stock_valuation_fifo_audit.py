# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

class StockValuationFifoAudit(models.Model):
    _name = 'stock.valuation.fifo.audit'
    _description = 'Inventory Valuation & FIFO GL Audit'
    _order = 'as_of_date desc, id desc'

    name = fields.Char(
        string='Audit Reference',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New Audit')
    )
    as_of_date = fields.Datetime(
        string='As of Date',
        required=True,
        default=fields.Datetime.now,
        help="The cut-off date and time for valuation moves and GL journal items."
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        related='company_id.currency_id',
        readonly=True
    )
    category_ids = fields.Many2many(
        'product.category',
        string='Product Categories',
        help="Optional filter: leave blank to audit all product categories."
    )
    product_ids = fields.Many2many(
        'product.product',
        string='Specific Products',
        help="Optional filter: leave blank to audit all products."
    )
    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('computed', 'Computed'),
        ],
        string='Status',
        default='draft',
        readonly=True
    )
    line_ids = fields.One2many(
        'stock.valuation.fifo.audit.line',
        'audit_id',
        string='Valuation Lines',
        copy=False
    )

    # Summary Totals
    total_svl_value = fields.Monetary(
        string='Total Physical SVL Value',
        compute='_compute_totals',
        store=True,
        currency_field='currency_id'
    )
    total_gl_value = fields.Monetary(
        string='Total GL Stock Balance',
        compute='_compute_totals',
        store=True,
        currency_field='currency_id'
    )
    total_discrepancy = fields.Monetary(
        string='Net Discrepancy',
        compute='_compute_totals',
        store=True,
        currency_field='currency_id'
    )
    total_open_fifo_layers = fields.Integer(
        string='Total Open FIFO Layers',
        compute='_compute_totals',
        store=True
    )
    total_products_count = fields.Integer(
        string='Products Audited',
        compute='_compute_totals',
        store=True
    )
    discrepancy_count = fields.Integer(
        string='Discrepancies Found',
        compute='_compute_totals',
        store=True
    )
    has_discrepancy = fields.Boolean(
        string='Has Reconciliation Variance',
        compute='_compute_totals',
        store=True
    )

    @api.depends('line_ids', 'line_ids.svl_value', 'line_ids.gl_balance', 'line_ids.discrepancy', 'line_ids.open_layers_count')
    def _compute_totals(self):
        for audit in self:
            svl_val = sum(line.svl_value for line in audit.line_ids)
            gl_val = sum(line.gl_balance for line in audit.line_ids)
            discrepancies = [line for line in audit.line_ids if line.status == 'discrepancy']
            audit.total_svl_value = svl_val
            audit.total_gl_value = gl_val
            audit.total_discrepancy = svl_val - gl_val
            audit.total_open_fifo_layers = sum(line.open_layers_count for line in audit.line_ids)
            audit.total_products_count = len(audit.line_ids)
            audit.discrepancy_count = len(discrepancies)
            audit.has_discrepancy = bool(discrepancies or abs(audit.total_discrepancy) > 0.01)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New Audit')) == _('New Audit'):
                vals['name'] = self.env['ir.sequence'].next_by_code('stock.valuation.fifo.audit') or \
                               f"VAL-AUDIT/{fields.Date.today().strftime('%Y%m%d')}-{self.env['ir.sequence'].next_by_code('base') or '001'}"
        return super().create(vals_list)

    def action_compute_audit(self):
        self.ensure_one()
        self.line_ids.unlink()

        # Build product domain
        if self.product_ids:
            products = self.product_ids
        elif self.category_ids:
            products = self.env['product.product'].search([
                ('categ_id', 'child_of', self.category_ids.ids)
            ])
        else:
            # Query products having valuation stock moves up to as_of_date in Odoo 19
            self.env.cr.execute("""
                SELECT DISTINCT product_id
                FROM stock_move
                WHERE company_id = %s
                  AND state = 'done'
                  AND (is_in = TRUE OR is_out = TRUE)
                  AND date <= %s
            """, (self.company_id.id, self.as_of_date))
            product_ids = [row[0] for row in self.env.cr.fetchall()]
            products = self.env['product.product'].browse(product_ids)

        if not products:
            raise UserError(_("No products found with stock valuation moves up to %s.") % self.as_of_date)

        lines_to_create = []
        cutoff_date_str = self.as_of_date.strftime('%Y-%m-%d %H:%M:%S')
        cutoff_date_only = self.as_of_date.date()

        for product in products:
            # 1. Physical Valuation Totals from stock_move in Odoo 19
            self.env.cr.execute("""
                SELECT
                    COALESCE(SUM(CASE WHEN is_in THEN quantity WHEN is_out THEN -quantity ELSE quantity END), 0.0) as qty,
                    COALESCE(SUM(CASE WHEN is_in THEN value WHEN is_out THEN -value ELSE value END), 0.0) as val
                FROM stock_move
                WHERE product_id = %s
                  AND company_id = %s
                  AND state = 'done'
                  AND (is_in = TRUE OR is_out = TRUE)
                  AND date <= %s
            """, (product.id, self.company_id.id, cutoff_date_str))
            svl_row = self.env.cr.fetchone()
            svl_qty = svl_row[0] if svl_row else 0.0
            svl_val = svl_row[1] if svl_row else 0.0

            # 2. FIFO Active Open Layers on stock_move in Odoo 19
            self.env.cr.execute("""
                SELECT
                    COALESCE(SUM(remaining_qty), 0.0) as fifo_qty,
                    COALESCE(SUM(remaining_value), 0.0) as fifo_val,
                    COUNT(id) as open_count
                FROM stock_move
                WHERE product_id = %s
                  AND company_id = %s
                  AND state = 'done'
                  AND is_in = TRUE
                  AND remaining_qty > 0
                  AND date <= %s
            """, (product.id, self.company_id.id, cutoff_date_str))
            fifo_row = self.env.cr.fetchone()
            fifo_qty = fifo_row[0] if fifo_row else 0.0
            fifo_val = fifo_row[1] if fifo_row else 0.0
            open_count = fifo_row[2] if fifo_row else 0

            # 3. Stock Valuation Account Resolution
            categ = product.categ_id
            valuation_account = getattr(categ, 'property_stock_valuation_account_id', False)
            if not valuation_account and hasattr(product, 'property_stock_valuation_account_id'):
                valuation_account = product.property_stock_valuation_account_id

            gl_balance = 0.0
            status = 'reconciled'
            notes = []

            if not valuation_account:
                status = 'no_account'
                notes.append(_("Warning: No Stock Valuation Account configured on category %s.") % categ.display_name)
            else:
                # 4. GL Account Balance for this product
                self.env.cr.execute("""
                    SELECT COALESCE(SUM(debit - credit), 0.0)
                    FROM account_move_line aml
                    JOIN account_move am ON am.id = aml.move_id
                    WHERE aml.company_id = %s
                      AND aml.account_id = %s
                      AND aml.product_id = %s
                      AND aml.date <= %s
                      AND am.state = 'posted'
                """, (self.company_id.id, valuation_account.id, product.id, cutoff_date_only))
                gl_row = self.env.cr.fetchone()
                gl_balance = gl_row[0] if gl_row else 0.0

                discrepancy = svl_val - gl_balance
                if abs(discrepancy) > 0.01:
                    status = 'discrepancy'
                    notes.append(_("Discrepancy: Physical stock value (%s) differs from GL posted balance (%s).") % (
                        f"{svl_val:,.2f}", f"{gl_balance:,.2f}"
                    ))
                    # Check for draft stock accounting entries
                    self.env.cr.execute("""
                        SELECT COUNT(aml.id)
                        FROM account_move_line aml
                        JOIN account_move am ON am.id = aml.move_id
                        WHERE aml.company_id = %s
                          AND aml.account_id = %s
                          AND aml.product_id = %s
                          AND aml.date <= %s
                          AND am.state = 'draft'
                    """, (self.company_id.id, valuation_account.id, product.id, cutoff_date_only))
                    draft_count = self.env.cr.fetchone()[0]
                    if draft_count:
                        notes.append(_("Found %d unposted (draft) journal lines on valuation account.") % draft_count)

            # 5. COGS Verification on stock_move
            self.env.cr.execute("""
                SELECT COUNT(sm.id)
                FROM stock_move sm
                LEFT JOIN account_move am ON am.id = sm.account_move_id
                WHERE sm.product_id = %s
                  AND sm.company_id = %s
                  AND sm.state = 'done'
                  AND sm.is_out = TRUE
                  AND sm.date <= %s
                  AND (sm.account_move_id IS NULL OR am.state != 'posted')
            """, (product.id, self.company_id.id, cutoff_date_str))
            cogs_issue_count = self.env.cr.fetchone()[0]

            self.env.cr.execute("""
                SELECT COUNT(id)
                FROM stock_move
                WHERE product_id = %s AND company_id = %s AND state = 'done' AND is_out = TRUE AND date <= %s
            """, (product.id, self.company_id.id, cutoff_date_str))
            outgoing_count = self.env.cr.fetchone()[0]

            if outgoing_count == 0:
                cogs_verification = 'na'
            elif cogs_issue_count > 0:
                cogs_verification = 'issues'
                notes.append(_("%d outgoing deliveries lack a posted COGS/Stock journal entry.") % cogs_issue_count)
            else:
                cogs_verification = 'verified'

            lines_to_create.append({
                'audit_id': self.id,
                'product_id': product.id,
                'product_code': product.default_code or '',
                'categ_id': categ.id,
                'uom_id': product.uom_id.id,
                'company_id': self.company_id.id,
                'valuation_account_id': valuation_account.id if valuation_account else False,
                'svl_qty': svl_qty,
                'svl_value': svl_val,
                'fifo_remaining_qty': fifo_qty,
                'fifo_remaining_value': fifo_val,
                'open_layers_count': open_count,
                'fifo_avg_unit_cost': (fifo_val / fifo_qty) if fifo_qty else (svl_val / svl_qty if svl_qty else 0.0),
                'gl_balance': gl_balance,
                'discrepancy': svl_val - gl_balance,
                'status': status,
                'cogs_verification': cogs_verification,
                'notes': "\n".join(notes) if notes else _("Fully reconciled. FIFO layers active."),
            })

        self.env['stock.valuation.fifo.audit.line'].create(lines_to_create)
        self.state = 'computed'
        return True

    def action_print_pdf(self):
        self.ensure_one()
        return self.env.ref('account_enterprise_ce.action_report_stock_valuation_fifo').report_action(self)

    def action_view_discrepancies(self):
        self.ensure_one()
        return {
            'name': _('Valuation Discrepancies (%s)') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'stock.valuation.fifo.audit.line',
            'view_mode': 'list,form',
            'domain': [('audit_id', '=', self.id), ('status', '=', 'discrepancy')],
            'context': {'default_audit_id': self.id},
        }


class StockValuationFifoAuditLine(models.Model):
    _name = 'stock.valuation.fifo.audit.line'
    _description = 'Valuation Audit Line'
    _order = 'status desc, discrepancy desc, product_id asc'

    audit_id = fields.Many2one(
        'stock.valuation.fifo.audit',
        string='Audit Reference',
        required=True,
        ondelete='cascade'
    )
    as_of_date = fields.Datetime(
        related='audit_id.as_of_date',
        readonly=True
    )
    product_id = fields.Many2one(
        'product.product',
        string='Product',
        required=True
    )
    product_code = fields.Char(
        string='Internal Reference',
        readonly=True
    )
    categ_id = fields.Many2one(
        'product.category',
        string='Category',
        required=True
    )
    uom_id = fields.Many2one(
        'uom.uom',
        string='Unit of Measure'
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        related='company_id.currency_id',
        readonly=True
    )
    valuation_account_id = fields.Many2one(
        'account.account',
        string='Valuation Account'
    )

    # Quantities & Values
    svl_qty = fields.Float(
        string='SVL On-Hand Qty',
        digits='Product Unit of Measure'
    )
    svl_value = fields.Monetary(
        string='Physical SVL Value',
        currency_field='currency_id'
    )
    fifo_remaining_qty = fields.Float(
        string='FIFO Open Qty',
        digits='Product Unit of Measure'
    )
    fifo_remaining_value = fields.Monetary(
        string='FIFO Open Value',
        currency_field='currency_id'
    )
    open_layers_count = fields.Integer(
        string='Open Layers'
    )
    fifo_avg_unit_cost = fields.Float(
        string='FIFO Unit Cost',
        digits='Product Price'
    )
    gl_balance = fields.Monetary(
        string='GL Balance',
        currency_field='currency_id'
    )
    discrepancy = fields.Monetary(
        string='Variance (SVL - GL)',
        currency_field='currency_id'
    )
    status = fields.Selection(
        selection=[
            ('reconciled', 'Reconciled'),
            ('discrepancy', 'Discrepancy'),
            ('no_account', 'No Valuation Account'),
        ],
        string='Audit Status',
        default='reconciled'
    )
    cogs_verification = fields.Selection(
        selection=[
            ('verified', 'All COGS Posted'),
            ('issues', 'Missing/Draft COGS'),
            ('na', 'No Outgoing Moves'),
        ],
        string='COGS Audit',
        default='na'
    )
    notes = fields.Text(
        string='Audit Diagnosis / Notes'
    )

    def action_view_fifo_layers(self):
        self.ensure_one()
        return {
            'name': _('FIFO Valuation Moves: %s') % self.product_id.display_name,
            'type': 'ir.actions.act_window',
            'res_model': 'stock.move',
            'view_mode': 'list,form',
            'domain': [
                ('product_id', '=', self.product_id.id),
                ('company_id', '=', self.company_id.id),
                ('state', '=', 'done'),
                '|', ('is_in', '=', True), ('is_out', '=', True),
                ('date', '<=', self.audit_id.as_of_date),
            ],
            'context': {
                'cost_method': 'fifo',
            },
        }

    def action_view_gl_items(self):
        self.ensure_one()
        if not self.valuation_account_id:
            raise UserError(_("No valuation account is set for this line."))
        return {
            'name': _('GL Journal Items: %s (%s)') % (self.valuation_account_id.code, self.product_id.display_name),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move.line',
            'view_mode': 'list,form',
            'domain': [
                ('company_id', '=', self.company_id.id),
                ('account_id', '=', self.valuation_account_id.id),
                ('product_id', '=', self.product_id.id),
                ('date', '<=', self.audit_id.as_of_date.date()),
                ('parent_state', '=', 'posted'),
            ],
        }

    def action_view_cogs_entries(self):
        self.ensure_one()
        moves = self.env['stock.move'].search([
            ('product_id', '=', self.product_id.id),
            ('company_id', '=', self.company_id.id),
            ('state', '=', 'done'),
            ('is_out', '=', True),
            ('date', '<=', self.audit_id.as_of_date),
        ])
        move_ids = [m.account_move_id.id for m in moves if m.account_move_id]
        return {
            'name': _('COGS Journal Entries: %s') % self.product_id.display_name,
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('id', 'in', move_ids)],
        }
