# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class StockValuationFifoWizard(models.TransientModel):
    _name = 'stock.valuation.fifo.wizard'
    _description = 'Inventory Valuation & FIFO Audit Wizard'

    as_of_date = fields.Datetime(
        string='Valuation As of Date',
        required=True,
        default=fields.Datetime.now,
        help="Target date and time for FIFO cost layer audit and GL balance reconciliation."
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company
    )
    category_ids = fields.Many2many(
        'product.category',
        string='Product Categories',
        help="Leave blank to include all product categories."
    )
    product_ids = fields.Many2many(
        'product.product',
        string='Specific Products',
        help="Leave blank to include all storable/valued products."
    )
    only_discrepancies = fields.Boolean(
        string='Filter Discrepancies Only',
        default=False,
        help="Check to immediately display only products where SVL physical value does not match GL balance."
    )

    def action_generate_audit(self):
        self.ensure_one()
        audit = self.env['stock.valuation.fifo.audit'].create({
            'as_of_date': self.as_of_date,
            'company_id': self.company_id.id,
            'category_ids': [(6, 0, self.category_ids.ids)],
            'product_ids': [(6, 0, self.product_ids.ids)],
        })
        audit.action_compute_audit()

        if self.only_discrepancies:
            return audit.action_view_discrepancies()

        return {
            'name': _('Inventory Valuation & FIFO Audit (%s)') % audit.name,
            'type': 'ir.actions.act_window',
            'res_model': 'stock.valuation.fifo.audit',
            'res_id': audit.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_generate_and_print(self):
        self.ensure_one()
        audit = self.env['stock.valuation.fifo.audit'].create({
            'as_of_date': self.as_of_date,
            'company_id': self.company_id.id,
            'category_ids': [(6, 0, self.category_ids.ids)],
            'product_ids': [(6, 0, self.product_ids.ids)],
        })
        audit.action_compute_audit()
        return audit.action_print_pdf()
