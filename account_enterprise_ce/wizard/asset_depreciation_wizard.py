# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class AssetDepreciationWizard(models.TransientModel):
    _name = 'asset.depreciation.wizard'
    _description = 'Generate Asset Depreciation Entries'

    date = fields.Date(
        string='Depreciation Up To Date',
        required=True,
        default=fields.Date.today,
        help="All due asset depreciation installments up to this date will have journal entries generated."
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company
    )
    post_immediately = fields.Boolean(
        string='Post Entries Immediately',
        default=False,
        help="Check to automatically post the journal entries. If unchecked, entries are generated in 'Draft' state for accountant review."
    )

    def action_generate_depreciation_entries(self):
        self.ensure_one()
        lines = self.env['account.asset.depreciation.line'].search([
            ('asset_id.state', '=', 'open'),
            ('asset_id.company_id', '=', self.company_id.id),
            ('depreciation_date', '<=', self.date),
            ('move_id', '=', False),
            ('amount', '>', 0),
        ])

        if not lines:
            raise UserError(_("There are no due depreciation installments to generate for the selected date."))

        lines.create_move(post_entry=self.post_immediately)
        move_ids = lines.mapped('move_id').ids

        action_name = _('Generated Depreciation Journal Entries')
        return {
            'name': action_name,
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('id', 'in', move_ids)],
            'context': {'default_move_type': 'entry'},
        }
