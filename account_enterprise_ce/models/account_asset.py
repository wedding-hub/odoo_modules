# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from dateutil.relativedelta import relativedelta
import calendar
import logging

_logger = logging.getLogger(__name__)

class AccountAssetCategory(models.Model):
    _name = 'account.asset.category'
    _description = 'Asset Model / Template'
    _order = 'name asc'

    name = fields.Char(string='Asset Model Name', required=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', string='Currency', related='company_id.currency_id', readonly=True)

    method = fields.Selection([
        ('linear', 'Straight-Line'),
        ('degressive', 'Declining Balance (Degressive)'),
    ], string='Computation Method', required=True, default='linear')

    method_number = fields.Integer(string='Number of Depreciations', default=5, required=True,
                                   help="The number of depreciations needed to depreciate your asset.")
    method_period = fields.Selection([
        ('1', 'Months'),
        ('12', 'Years'),
    ], string='Period Frequency', required=True, default='12',
        help="Frequency of the depreciation installment.")
    method_progress_factor = fields.Float(string='Degressive Factor', default=0.3,
                                          help="Degressive rate used for Declining Balance calculation (e.g. 0.3 for 30%).")
    prorata = fields.Boolean(string='Prorata Temporis', default=False,
                             help="Indicates that the first depreciation period begins exactly on the purchase date.")

    account_asset_id = fields.Many2one('account.account', string='Asset Account', required=True,
                                       help="Account used to record the purchase / gross cost of the asset.")
    account_depreciation_id = fields.Many2one('account.account', string='Accumulated Depreciation Account', required=True,
                                             help="Account used to record accumulated depreciation.")
    account_depreciation_expense_id = fields.Many2one('account.account', string='Depreciation Expense Account', required=True,
                                                     help="Expense account used to record periodic depreciation costs.")
    journal_id = fields.Many2one('account.journal', string='Depreciation Journal', required=True,
                                 domain="[('type', '=', 'general'), ('company_id', '=', company_id)]")
    auto_create_from_bill = fields.Boolean(string='Auto-create Asset from Bill', default=True,
                                           help="When a vendor bill line uses this asset model, a draft asset is automatically generated.")


class AccountAsset(models.Model):
    _name = 'account.asset'
    _description = 'Fixed Asset'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'

    name = fields.Char(string='Asset Name', required=True, tracking=True)
    code = fields.Char(string='Asset Code / Tag', copy=False)
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', string='Currency', related='company_id.currency_id', readonly=True)
    category_id = fields.Many2one('account.asset.category', string='Asset Model', required=True, tracking=True)

    date = fields.Date(string='Acquisition Date', required=True, default=fields.Date.today, tracking=True)
    first_depreciation_date = fields.Date(string='First Depreciation Date', help="Date for first depreciation installment.")

    original_value = fields.Monetary(string='Gross Acquisition Cost', required=True, currency_field='currency_id', tracking=True)
    salvage_value = fields.Monetary(string='Residual / Salvage Value', default=0.0, currency_field='currency_id',
                                    help="Estimated scrap value at the end of the asset useful life.")
    value_residual = fields.Monetary(string='Net Book Value', compute='_compute_values', store=True, currency_field='currency_id')
    value_depreciated = fields.Monetary(string='Cumulative Depreciation', compute='_compute_values', store=True, currency_field='currency_id')

    method = fields.Selection([
        ('linear', 'Straight-Line'),
        ('degressive', 'Declining Balance (Degressive)'),
    ], string='Computation Method', required=True, default='linear')
    method_number = fields.Integer(string='Number of Depreciations', default=5, required=True)
    method_period = fields.Selection([
        ('1', 'Months'),
        ('12', 'Years'),
    ], string='Period Frequency', required=True, default='12')
    method_progress_factor = fields.Float(string='Degressive Factor', default=0.3)
    prorata = fields.Boolean(string='Prorata Temporis', default=False)

    account_asset_id = fields.Many2one('account.account', string='Asset Account', required=True)
    account_depreciation_id = fields.Many2one('account.account', string='Accumulated Depreciation Account', required=True)
    account_depreciation_expense_id = fields.Many2one('account.account', string='Depreciation Expense Account', required=True)
    journal_id = fields.Many2one('account.journal', string='Depreciation Journal', required=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('open', 'Running'),
        ('paused', 'Paused'),
        ('close', 'Disposed / Closed'),
    ], string='Status', default='draft', tracking=True, readonly=True)

    depreciation_line_ids = fields.One2many('account.asset.depreciation.line', 'asset_id', string='Depreciation Board', copy=False)
    invoice_id = fields.Many2one('account.move', string='Vendor Bill', readonly=True, copy=False)

    @api.onchange('category_id')
    def _onchange_category_id(self):
        if self.category_id:
            self.method = self.category_id.method
            self.method_number = self.category_id.method_number
            self.method_period = self.category_id.method_period
            self.method_progress_factor = self.category_id.method_progress_factor
            self.prorata = self.category_id.prorata
            self.account_asset_id = self.category_id.account_asset_id
            self.account_depreciation_id = self.category_id.account_depreciation_id
            self.account_depreciation_expense_id = self.category_id.account_depreciation_expense_id
            self.journal_id = self.category_id.journal_id

    @api.depends('original_value', 'salvage_value', 'depreciation_line_ids.amount', 'depreciation_line_ids.move_posted_check')
    def _compute_values(self):
        for asset in self:
            posted_lines = asset.depreciation_line_ids.filtered(lambda l: l.move_posted_check)
            total_depreciated = sum(line.amount for line in posted_lines)
            asset.value_depreciated = total_depreciated
            asset.value_residual = max(0.0, asset.original_value - total_depreciated)

    def compute_depreciation_board(self):
        self.ensure_one()
        # Keep already posted lines
        posted_lines = self.depreciation_line_ids.filtered(lambda l: l.move_posted_check or l.state == 'posted')
        unposted_lines = self.depreciation_line_ids - posted_lines
        unposted_lines.unlink()

        if self.original_value <= self.salvage_value:
            return True

        posted_amount = sum(line.amount for line in posted_lines)
        depreciable_base = self.original_value - self.salvage_value - posted_amount
        if depreciable_base <= 0:
            return True

        num_periods = self.method_number - len(posted_lines)
        if num_periods <= 0:
            return True

        lines_to_create = []
        start_date = self.first_depreciation_date or self.date
        months_per_period = int(self.method_period)

        current_date = start_date
        accumulated = posted_amount
        remaining = self.original_value - accumulated

        # Prorata handling for first installment
        prorata_ratio = 1.0
        if self.prorata:
            # Calculate proportion of period remaining in current period
            if months_per_period == 1:
                total_days = calendar.monthrange(start_date.year, start_date.month)[1]
                remaining_days = total_days - start_date.day + 1
                prorata_ratio = remaining_days / float(total_days)
            else:
                day_of_year = start_date.timetuple().tm_yday
                days_in_year = 366 if calendar.isleap(start_date.year) else 365
                prorata_ratio = (days_in_year - day_of_year + 1) / float(days_in_year)

        total_installments = num_periods + (1 if (self.prorata and prorata_ratio < 0.999) else 0)
        curr_residual_cost = remaining - self.salvage_value

        for i in range(total_installments):
            seq = len(posted_lines) + i + 1
            # Determine period end date
            target_date = start_date + relativedelta(months=months_per_period * (i + 1))
            # Normalize to last day of month
            last_day = calendar.monthrange(target_date.year, target_date.month)[1]
            installment_date = target_date.replace(day=last_day)

            # Calculation amount
            if i == 0 and self.prorata and prorata_ratio < 0.999:
                if self.method == 'linear':
                    installment_amount = (depreciable_base / float(num_periods)) * prorata_ratio
                else:
                    installment_amount = curr_residual_cost * self.method_progress_factor * prorata_ratio
            elif i == total_installments - 1:
                # Final balancing period takes remaining depreciable base
                installment_amount = max(0.0, curr_residual_cost)
            else:
                if self.method == 'linear':
                    installment_amount = depreciable_base / float(num_periods)
                else:
                    degressive_amount = curr_residual_cost * self.method_progress_factor
                    linear_equiv = curr_residual_cost / float(total_installments - i)
                    installment_amount = max(degressive_amount, linear_equiv)

            installment_amount = min(installment_amount, curr_residual_cost)
            installment_amount = self.currency_id.round(installment_amount)

            if installment_amount <= 0 and i < total_installments - 1:
                continue

            curr_residual_cost -= installment_amount
            accumulated += installment_amount
            book_value = self.original_value - accumulated

            lines_to_create.append({
                'asset_id': self.id,
                'name': f"{self.name} - {seq}/{total_installments}",
                'sequence': seq,
                'depreciation_date': installment_date,
                'amount': installment_amount,
                'depreciated_value': accumulated,
                'remaining_value': max(0.0, book_value),
                'state': 'draft',
            })

            if curr_residual_cost <= 0:
                break

        if lines_to_create:
            self.env['account.asset.depreciation.line'].create(lines_to_create)
        return True

    def action_confirm(self):
        for asset in self:
            if not asset.depreciation_line_ids:
                asset.compute_depreciation_board()
            asset.state = 'open'
        return True

    def action_pause(self):
        self.write({'state': 'paused'})

    def action_resume(self):
        self.write({'state': 'open'})

    def action_close(self):
        self.write({'state': 'close'})

    def action_draft(self):
        # Only allow if no lines are posted
        for asset in self:
            if any(line.move_posted_check for line in asset.depreciation_line_ids):
                raise UserError(_("Cannot reset to draft an asset with posted depreciation entries."))
            asset.depreciation_line_ids.unlink()
            asset.state = 'draft'
        return True


class AccountAssetDepreciationLine(models.Model):
    _name = 'account.asset.depreciation.line'
    _description = 'Asset Depreciation Line'
    _order = 'depreciation_date asc, id asc'

    asset_id = fields.Many2one('account.asset', string='Asset', required=True, ondelete='cascade')
    name = fields.Char(string='Installment Reference', required=True)
    sequence = fields.Integer(string='Sequence', default=1)
    depreciation_date = fields.Date(string='Depreciation Date', required=True)
    amount = fields.Monetary(string='Depreciation Amount', required=True, currency_field='currency_id')
    depreciated_value = fields.Monetary(string='Cumulative Depreciation', currency_field='currency_id')
    remaining_value = fields.Monetary(string='Book Value', currency_field='currency_id')

    company_id = fields.Many2one('res.company', related='asset_id.company_id', store=True, readonly=True)
    currency_id = fields.Many2one('res.currency', related='asset_id.currency_id', store=True, readonly=True)

    move_id = fields.Many2one('account.move', string='Depreciation Entry', copy=False)
    move_posted_check = fields.Boolean(string='Posted', compute='_compute_move_posted', store=True)
    state = fields.Selection([
        ('draft', 'Unposted'),
        ('posted', 'Posted'),
    ], string='Status', default='draft')

    @api.depends('move_id', 'move_id.state')
    def _compute_move_posted(self):
        for line in self:
            line.move_posted_check = bool(line.move_id and line.move_id.state == 'posted')
            if line.move_posted_check:
                line.state = 'posted'

    def create_move(self, post_entry=False):
        for line in self:
            if line.move_id:
                continue
            if line.amount <= 0:
                continue

            asset = line.asset_id
            move_vals = {
                'date': line.depreciation_date,
                'ref': f"{asset.name} - {line.name}",
                'journal_id': asset.journal_id.id,
                'company_id': asset.company_id.id,
                'move_type': 'entry',
                'line_ids': [
                    (0, 0, {
                        'name': line.name,
                        'account_id': asset.account_depreciation_expense_id.id,
                        'debit': line.amount,
                        'credit': 0.0,
                        'journal_id': asset.journal_id.id,
                        'date': line.depreciation_date,
                    }),
                    (0, 0, {
                        'name': line.name,
                        'account_id': asset.account_depreciation_id.id,
                        'debit': 0.0,
                        'credit': line.amount,
                        'journal_id': asset.journal_id.id,
                        'date': line.depreciation_date,
                    }),
                ],
            }
            move = self.env['account.move'].create(move_vals)
            line.move_id = move.id
            if post_entry:
                move.action_post()
                line.state = 'posted'
        return True
