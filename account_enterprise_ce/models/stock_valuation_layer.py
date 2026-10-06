# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class StockMove(models.Model):
    _inherit = 'stock.move'

    fifo_layer_status = fields.Selection(
        selection=[
            ('open', 'Open Layer'),
            ('partial', 'Partially Consumed'),
            ('consumed', 'Fully Consumed'),
            ('out', 'Outgoing Consumption'),
        ],
        string='FIFO Status',
        compute='_compute_fifo_layer_status',
        store=True,
        help="Classification of the FIFO inventory layer in Odoo 19."
    )
    cogs_account_move_id = fields.Many2one(
        'account.move',
        string='Linked Accounting Entry',
        related='account_move_id',
        readonly=True,
        help="The accounting journal entry generated for this stock valuation move."
    )
    cogs_journal_state = fields.Selection(
        related='account_move_id.state',
        string='Entry State',
        readonly=True,
    )

    @api.depends('quantity', 'remaining_qty', 'is_in', 'is_out', 'state')
    def _compute_fifo_layer_status(self):
        for move in self:
            if move.is_out or move.quantity < 0:
                move.fifo_layer_status = 'out'
            elif float(move.remaining_qty or 0.0) == float(move.quantity or 0.0):
                move.fifo_layer_status = 'open'
            elif float(move.remaining_qty or 0.0) > 0:
                move.fifo_layer_status = 'partial'
            else:
                move.fifo_layer_status = 'consumed'

    def action_open_cogs_entry(self):
        self.ensure_one()
        move = self.account_move_id
        if not move:
            return {'type': 'ir.actions.act_window_close'}
        return {
            'name': _('Accounting Journal Entry'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id': move.id,
            'view_mode': 'form',
            'target': 'current',
        }
