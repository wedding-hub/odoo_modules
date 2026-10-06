# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

class AccountFinancialReport(models.AbstractModel):
    _name = 'account.financial.report'
    _description = 'Dynamic Financial Reporting Engine'

    @api.model
    def get_report_data(self, report_type, options=None):
        options = options or {}
        company = self.env.company
        today = fields.Date.today()

        date_to = options.get('date_to') or str(today)
        date_from = options.get('date_from') or str(today.replace(month=1, day=1))
        target_move = options.get('target_move') or 'posted'
        comparison = options.get('comparison', {})

        if report_type == 'balance_sheet':
            return self._get_balance_sheet(company, date_from, date_to, target_move, comparison, options)
        elif report_type == 'profit_and_loss':
            return self._get_profit_and_loss(company, date_from, date_to, target_move, comparison, options)
        elif report_type == 'trial_balance':
            return self._get_trial_balance(company, date_from, date_to, target_move, options)
        elif report_type == 'general_ledger':
            return self._get_general_ledger(company, date_from, date_to, target_move, options)
        elif report_type in ('aged_receivable', 'aged_payable'):
            return self._get_aged_partner_balance(company, date_to, target_move, report_type, options)
        else:
            raise UserError(_("Unsupported financial report type: %s") % report_type)

    # -------------------------------------------------------------------------
    # 1. BALANCE SHEET
    # -------------------------------------------------------------------------
    def _get_balance_sheet(self, company, date_from, date_to, target_move, comparison, options):
        state_condition = "AND m.state = 'posted'" if target_move == 'posted' else ""

        query = f"""
            SELECT
                a.id, a.code, a.name, a.account_type,
                COALESCE(SUM(l.debit - l.credit), 0.0) AS balance
            FROM account_account a
            JOIN account_account_res_company_rel rel ON rel.account_account_id = a.id AND rel.res_company_id = %s
            LEFT JOIN account_move_line l ON l.account_id = a.id AND l.date <= %s
            LEFT JOIN account_move m ON m.id = l.move_id {state_condition}
            GROUP BY a.id, a.code, a.name, a.account_type
            HAVING ABS(COALESCE(SUM(l.debit - l.credit), 0.0)) > 0.001
            ORDER BY a.code ASC
        """
        self.env.cr.execute(query, (company.id, date_to))
        rows = self.env.cr.dictfetchall()

        asset_types = ['asset_receivable', 'asset_cash', 'asset_current', 'asset_non_current', 'asset_prepayments', 'asset_fixed']
        liability_types = ['liability_payable', 'liability_credit_card', 'liability_current', 'liability_non_current']
        equity_types = ['equity', 'equity_unaffected']
        pnl_types = ['income', 'income_other', 'expense', 'expense_depreciation', 'expense_direct_cost']

        assets_lines = []
        liabilities_lines = []
        equity_lines = []
        current_year_earnings = 0.0

        for r in rows:
            acc_type = r['account_type']
            balance = r['balance']
            if acc_type in asset_types:
                assets_lines.append({
                    'id': r['id'],
                    'code': r['code'],
                    'name': r['name'],
                    'balance': balance,
                    'type': acc_type,
                })
            elif acc_type in liability_types:
                liabilities_lines.append({
                    'id': r['id'],
                    'code': r['code'],
                    'name': r['name'],
                    'balance': -balance,
                    'type': acc_type,
                })
            elif acc_type in equity_types:
                equity_lines.append({
                    'id': r['id'],
                    'code': r['code'],
                    'name': r['name'],
                    'balance': -balance,
                    'type': acc_type,
                })
            elif acc_type in pnl_types:
                current_year_earnings += (-balance)

        if abs(current_year_earnings) > 0.001:
            equity_lines.append({
                'id': 0,
                'code': '999999',
                'name': _('Current Year Unallocated Earnings'),
                'balance': current_year_earnings,
                'type': 'equity_unaffected',
            })

        total_assets = sum(l['balance'] for l in assets_lines)
        total_liabilities = sum(l['balance'] for l in liabilities_lines)
        total_equity = sum(l['balance'] for l in equity_lines)

        return {
            'report_name': _('Balance Sheet'),
            'company_name': company.name,
            'currency_symbol': company.currency_id.symbol,
            'currency_position': company.currency_id.position,
            'date_to': date_to,
            'sections': [
                {
                    'title': _('Assets'),
                    'lines': assets_lines,
                    'total': total_assets,
                },
                {
                    'title': _('Liabilities'),
                    'lines': liabilities_lines,
                    'total': total_liabilities,
                },
                {
                    'title': _('Equity'),
                    'lines': equity_lines,
                    'total': total_equity,
                },
            ],
            'total_assets': total_assets,
            'total_liabilities_equity': total_liabilities + total_equity,
            'is_balanced': abs(total_assets - (total_liabilities + total_equity)) < 0.01,
        }

    # -------------------------------------------------------------------------
    # 2. PROFIT AND LOSS
    # -------------------------------------------------------------------------
    def _get_profit_and_loss(self, company, date_from, date_to, target_move, comparison, options):
        state_condition = "AND m.state = 'posted'" if target_move == 'posted' else ""

        query = f"""
            SELECT
                a.id, a.code, a.name, a.account_type,
                COALESCE(SUM(l.credit - l.debit), 0.0) AS net_income
            FROM account_account a
            JOIN account_account_res_company_rel rel ON rel.account_account_id = a.id AND rel.res_company_id = %s
            JOIN account_move_line l ON l.account_id = a.id AND l.date >= %s AND l.date <= %s
            JOIN account_move m ON m.id = l.move_id {state_condition}
            WHERE a.account_type IN ('income', 'income_other', 'expense', 'expense_depreciation', 'expense_direct_cost')
            GROUP BY a.id, a.code, a.name, a.account_type
            HAVING ABS(COALESCE(SUM(l.credit - l.debit), 0.0)) > 0.001
            ORDER BY a.code ASC
        """
        self.env.cr.execute(query, (company.id, date_from, date_to))
        rows = self.env.cr.dictfetchall()

        operating_income = []
        cost_of_sales = []
        operating_expenses = []
        other_income_expenses = []

        for r in rows:
            acc_type = r['account_type']
            net = r['net_income']
            if acc_type == 'income':
                operating_income.append({'id': r['id'], 'code': r['code'], 'name': r['name'], 'balance': net})
            elif acc_type == 'expense_direct_cost':
                cost_of_sales.append({'id': r['id'], 'code': r['code'], 'name': r['name'], 'balance': -net})
            elif acc_type in ('expense', 'expense_depreciation'):
                operating_expenses.append({'id': r['id'], 'code': r['code'], 'name': r['name'], 'balance': -net})
            elif acc_type == 'income_other':
                other_income_expenses.append({'id': r['id'], 'code': r['code'], 'name': r['name'], 'balance': net})

        tot_income = sum(l['balance'] for l in operating_income)
        tot_cogs = sum(l['balance'] for l in cost_of_sales)
        gross_profit = tot_income - tot_cogs
        tot_expenses = sum(l['balance'] for l in operating_expenses)
        operating_profit = gross_profit - tot_expenses
        tot_other = sum(l['balance'] for l in other_income_expenses)
        net_profit = operating_profit + tot_other

        return {
            'report_name': _('Profit and Loss'),
            'company_name': company.name,
            'currency_symbol': company.currency_id.symbol,
            'currency_position': company.currency_id.position,
            'date_from': date_from,
            'date_to': date_to,
            'operating_income': {'lines': operating_income, 'total': tot_income},
            'cost_of_sales': {'lines': cost_of_sales, 'total': tot_cogs},
            'gross_profit': gross_profit,
            'operating_expenses': {'lines': operating_expenses, 'total': tot_expenses},
            'operating_profit': operating_profit,
            'other_income_expenses': {'lines': other_income_expenses, 'total': tot_other},
            'net_profit': net_profit,
        }

    # -------------------------------------------------------------------------
    # 3. TRIAL BALANCE
    # -------------------------------------------------------------------------
    def _get_trial_balance(self, company, date_from, date_to, target_move, options):
        state_condition = "AND m.state = 'posted'" if target_move == 'posted' else ""

        query = f"""
            SELECT
                a.id, a.code, a.name,
                COALESCE(SUM(CASE WHEN l.date < %s THEN (l.debit - l.credit) ELSE 0 END), 0.0) AS initial_balance,
                COALESCE(SUM(CASE WHEN l.date >= %s AND l.date <= %s THEN l.debit ELSE 0 END), 0.0) AS debit,
                COALESCE(SUM(CASE WHEN l.date >= %s AND l.date <= %s THEN l.credit ELSE 0 END), 0.0) AS credit
            FROM account_account a
            JOIN account_account_res_company_rel rel ON rel.account_account_id = a.id AND rel.res_company_id = %s
            LEFT JOIN account_move_line l ON l.account_id = a.id
            LEFT JOIN account_move m ON m.id = l.move_id {state_condition}
            GROUP BY a.id, a.code, a.name
            HAVING (
                ABS(COALESCE(SUM(CASE WHEN l.date < %s THEN (l.debit - l.credit) ELSE 0 END), 0.0)) > 0.001
                OR ABS(COALESCE(SUM(CASE WHEN l.date >= %s AND l.date <= %s THEN l.debit ELSE 0 END), 0.0)) > 0.001
                OR ABS(COALESCE(SUM(CASE WHEN l.date >= %s AND l.date <= %s THEN l.credit ELSE 0 END), 0.0)) > 0.001
            )
            ORDER BY a.code ASC
        """
        self.env.cr.execute(query, (
            date_from, date_from, date_to, date_from, date_to, company.id,
            date_from, date_from, date_to, date_from, date_to
        ))
        rows = self.env.cr.dictfetchall()

        lines = []
        tot_initial = 0.0
        tot_debit = 0.0
        tot_credit = 0.0
        tot_end = 0.0

        for r in rows:
            init = r['initial_balance']
            deb = r['debit']
            cred = r['credit']
            end_bal = init + deb - cred

            lines.append({
                'id': r['id'],
                'code': r['code'],
                'name': r['name'],
                'initial_balance': init,
                'debit': deb,
                'credit': cred,
                'end_balance': end_bal,
            })
            tot_initial += init
            tot_debit += deb
            tot_credit += cred
            tot_end += end_bal

        return {
            'report_name': _('Trial Balance'),
            'company_name': company.name,
            'currency_symbol': company.currency_id.symbol,
            'currency_position': company.currency_id.position,
            'date_from': date_from,
            'date_to': date_to,
            'lines': lines,
            'totals': {
                'initial_balance': tot_initial,
                'debit': tot_debit,
                'credit': tot_credit,
                'end_balance': tot_end,
            },
        }

    # -------------------------------------------------------------------------
    # 4. GENERAL LEDGER
    # -------------------------------------------------------------------------
    def _get_general_ledger(self, company, date_from, date_to, target_move, options):
        state_condition = "AND m.state = 'posted'" if target_move == 'posted' else ""
        account_ids = options.get('account_ids')

        acc_filter = ""
        params = [company.id, date_from, date_to]
        if account_ids:
            acc_filter = "AND a.id IN %s"
            params.append(tuple(account_ids))

        query = f"""
            SELECT
                l.id AS line_id,
                l.date,
                j.code AS journal_code,
                m.name AS move_name,
                l.ref,
                COALESCE(p.name, '') AS partner_name,
                l.name AS label,
                l.debit,
                l.credit,
                a.id AS account_id,
                a.code AS account_code,
                a.name AS account_name
            FROM account_move_line l
            JOIN account_move m ON m.id = l.move_id {state_condition}
            JOIN account_account a ON a.id = l.account_id
            JOIN account_journal j ON j.id = l.journal_id
            LEFT JOIN res_partner p ON p.id = l.partner_id
            WHERE l.company_id = %s
              AND l.date >= %s AND l.date <= %s
              {acc_filter}
            ORDER BY a.code ASC, l.date ASC, l.id ASC
        """
        self.env.cr.execute(query, tuple(params))
        rows = self.env.cr.dictfetchall()

        accounts_dict = {}
        for r in rows:
            acc_id = r['account_id']
            if acc_id not in accounts_dict:
                self.env.cr.execute(f"""
                    SELECT COALESCE(SUM(l.debit - l.credit), 0.0)
                    FROM account_move_line l
                    JOIN account_move m ON m.id = l.move_id {state_condition}
                    WHERE l.account_id = %s AND l.company_id = %s AND l.date < %s
                """, (acc_id, company.id, date_from))
                init_bal = self.env.cr.fetchone()[0]

                accounts_dict[acc_id] = {
                    'account_id': acc_id,
                    'account_code': r['account_code'],
                    'account_name': r['account_name'],
                    'initial_balance': init_bal,
                    'lines': [],
                    'total_debit': 0.0,
                    'total_credit': 0.0,
                    'ending_balance': init_bal,
                }

            acc = accounts_dict[acc_id]
            running_bal = acc['ending_balance'] + r['debit'] - r['credit']
            acc['lines'].append({
                'id': r['line_id'],
                'date': str(r['date']),
                'journal': r['journal_code'],
                'entry': r['move_name'],
                'partner': r['partner_name'],
                'label': r['label'] or r['ref'] or '',
                'debit': r['debit'],
                'credit': r['credit'],
                'balance': running_bal,
            })
            acc['total_debit'] += r['debit']
            acc['total_credit'] += r['credit']
            acc['ending_balance'] = running_bal

        return {
            'report_name': _('General Ledger'),
            'company_name': company.name,
            'currency_symbol': company.currency_id.symbol,
            'currency_position': company.currency_id.position,
            'date_from': date_from,
            'date_to': date_to,
            'accounts': list(accounts_dict.values()),
        }

    # -------------------------------------------------------------------------
    # 5. AGED RECEIVABLE & AGED PAYABLE
    # -------------------------------------------------------------------------
    def _get_aged_partner_balance(self, company, date_to, target_move, report_type, options):
        account_type = 'asset_receivable' if report_type == 'aged_receivable' else 'liability_payable'
        state_condition = "AND m.state = 'posted'" if target_move == 'posted' else ""

        query = f"""
            SELECT
                p.id AS partner_id,
                COALESCE(p.name, 'No Partner') AS partner_name,
                COALESCE(l.date_maturity, l.date) AS due_date,
                (l.debit - l.credit) AS amount_residual
            FROM account_move_line l
            JOIN account_move m ON m.id = l.move_id {state_condition}
            JOIN account_account a ON a.id = l.account_id
            LEFT JOIN res_partner p ON p.id = l.partner_id
            WHERE l.company_id = %s
              AND a.account_type = %s
              AND l.date <= %s
              AND l.reconciled = FALSE
            ORDER BY partner_name ASC
        """
        self.env.cr.execute(query, (company.id, account_type, date_to))
        rows = self.env.cr.dictfetchall()

        target_date = fields.Date.from_string(date_to)
        partners_data = {}

        for r in rows:
            p_id = r['partner_id'] or 0
            if p_id not in partners_data:
                partners_data[p_id] = {
                    'partner_name': r['partner_name'],
                    'current': 0.0,
                    'days_1_30': 0.0,
                    'days_31_60': 0.0,
                    'days_61_90': 0.0,
                    'days_91_120': 0.0,
                    'days_120_plus': 0.0,
                    'total': 0.0,
                }

            amt = r['amount_residual'] if report_type == 'aged_receivable' else -r['amount_residual']
            due_date = r['due_date']
            days_overdue = (target_date - due_date).days if due_date else 0

            if days_overdue <= 0:
                partners_data[p_id]['current'] += amt
            elif 1 <= days_overdue <= 30:
                partners_data[p_id]['days_1_30'] += amt
            elif 31 <= days_overdue <= 60:
                partners_data[p_id]['days_31_60'] += amt
            elif 61 <= days_overdue <= 90:
                partners_data[p_id]['days_61_90'] += amt
            elif 91 <= days_overdue <= 120:
                partners_data[p_id]['days_91_120'] += amt
            else:
                partners_data[p_id]['days_120_plus'] += amt

            partners_data[p_id]['total'] += amt

        valid_partners = [p for p in partners_data.values() if abs(p['total']) > 0.01]

        totals = {
            'current': sum(p['current'] for p in valid_partners),
            'days_1_30': sum(p['days_1_30'] for p in valid_partners),
            'days_31_60': sum(p['days_31_60'] for p in valid_partners),
            'days_61_90': sum(p['days_61_90'] for p in valid_partners),
            'days_91_120': sum(p['days_91_120'] for p in valid_partners),
            'days_120_plus': sum(p['days_120_plus'] for p in valid_partners),
            'total': sum(p['total'] for p in valid_partners),
        }

        title = _('Aged Receivable') if report_type == 'aged_receivable' else _('Aged Payable')
        return {
            'report_name': title,
            'report_type': report_type,
            'company_name': company.name,
            'currency_symbol': company.currency_id.symbol,
            'currency_position': company.currency_id.position,
            'date_to': date_to,
            'partners': valid_partners,
            'totals': totals,
        }
