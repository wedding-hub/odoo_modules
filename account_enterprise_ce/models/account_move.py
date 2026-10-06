# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class AccountMove(models.Model):
    _inherit = 'account.move'

    asset_count = fields.Integer(string='Asset Count', compute='_compute_asset_count')

    def _compute_asset_count(self):
        for move in self:
            move.asset_count = self.env['account.asset'].search_count([('invoice_id', '=', move.id)])

    def action_open_assets(self):
        self.ensure_one()
        return {
            'name': _('Assets Generated'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.asset',
            'view_mode': 'list,form',
            'domain': [('invoice_id', '=', self.id)],
            'context': {'default_invoice_id': self.id},
        }

    def action_post(self):
        res = super().action_post()
        for move in self:
            if move.move_type in ('in_invoice', 'in_refund'):
                for line in move.invoice_line_ids:
                    if line.asset_category_id and line.asset_category_id.auto_create_from_bill:
                        # Create draft asset
                        vals = {
                            'name': line.name or f"{move.name} - {line.product_id.name or 'Asset'}",
                            'category_id': line.asset_category_id.id,
                            'company_id': move.company_id.id,
                            'date': move.invoice_date or move.date or fields.Date.today(),
                            'first_depreciation_date': move.invoice_date or move.date,
                            'original_value': abs(line.price_subtotal),
                            'invoice_id': move.id,
                            'state': 'draft',
                        }
                        asset = self.env['account.asset'].create(vals)
                        asset._onchange_category_id()
                        asset.compute_depreciation_board()
        return res


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    asset_category_id = fields.Many2one(
        'account.asset.category',
        string='Asset Model',
        domain="[('company_id', '=', company_id)]",
        help="Select an Asset Model to automatically create a fixed asset upon posting this vendor bill."
    )
