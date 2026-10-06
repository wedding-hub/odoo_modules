# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class FinancialReportWizard(models.TransientModel):
    _name = 'financial.report.wizard'
    _description = 'Financial Report Filter Wizard'

    report_type = fields.Selection([
        ('balance_sheet', 'Balance Sheet'),
        ('profit_and_loss', 'Profit and Loss'),
        ('trial_balance', 'Trial Balance'),
        ('general_ledger', 'General Ledger'),
        ('aged_receivable', 'Aged Receivable'),
        ('aged_payable', 'Aged Payable'),
    ], string='Report Type', required=True, default='balance_sheet')

    date_from = fields.Date(
        string='Start Date',
        default=lambda self: fields.Date.today().replace(month=1, day=1)
    )
    date_to = fields.Date(
        string='End Date',
        required=True,
        default=fields.Date.today
    )
    target_move = fields.Selection([
        ('posted', 'All Posted Entries'),
        ('all', 'All Entries (Draft & Posted)'),
    ], string='Target Moves', required=True, default='posted')

    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company
    )

    def action_open_dynamic_report(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.client',
            'tag': 'account_financial_report_widget',
            'name': dict(self._fields['report_type'].selection).get(self.report_type, _('Financial Report')),
            'context': {
                'report_type': self.report_type,
                'date_from': str(self.date_from) if self.date_from else False,
                'date_to': str(self.date_to),
                'target_move': self.target_move,
            },
        }

    def action_print_pdf(self):
        self.ensure_one()
        report_data = self.env['account.financial.report'].get_report_data(
            self.report_type,
            options={
                'date_from': str(self.date_from) if self.date_from else False,
                'date_to': str(self.date_to),
                'target_move': self.target_move,
            }
        )
        return self.env.ref('account_enterprise_ce.action_report_financial_statement').report_action(
            self, data={'report_data': report_data, 'wizard_id': self.id}
        )
