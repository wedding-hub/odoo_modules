/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class FinancialReportWidget extends Component {
    static template = "account_enterprise_ce.FinancialReportWidget";

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");

        const ctx = this.props.action.context || {};
        const today = new Date().toISOString().split("T")[0];
        const yearStart = `${new Date().getFullYear()}-01-01`;

        this.state = useState({
            reportType: ctx.report_type || "balance_sheet",
            dateFrom: ctx.date_from || yearStart,
            dateTo: ctx.date_to || today,
            targetMove: ctx.target_move || "posted",
            isLoading: true,
            data: null,
            unfoldedAccounts: new Set(),
        });

        onWillStart(async () => {
            await this.loadReportData();
        });
    }

    async loadReportData() {
        this.state.isLoading = true;
        try {
            const data = await this.orm.call(
                "account.financial.report",
                "get_report_data",
                [this.state.reportType],
                {
                    options: {
                        date_from: this.state.dateFrom,
                        date_to: this.state.dateTo,
                        target_move: this.state.targetMove,
                    },
                }
            );
            this.state.data = data;
        } catch (error) {
            this.notification.add(error.message || "Failed to load financial report.", { type: "danger" });
        } finally {
            this.state.isLoading = false;
        }
    }

    async onReportChange(ev) {
        this.state.reportType = ev.target.value;
        this.state.unfoldedAccounts.clear();
        await this.loadReportData();
    }

    async onTargetMoveChange(ev) {
        this.state.targetMove = ev.target.value;
        await this.loadReportData();
    }

    async onDateFromChange(ev) {
        this.state.dateFrom = ev.target.value;
        await this.loadReportData();
    }

    async onDateToChange(ev) {
        this.state.dateTo = ev.target.value;
        await this.loadReportData();
    }

    setPreset(preset) {
        const now = new Date();
        const y = now.getFullYear();
        if (preset === "this_month") {
            const m = String(now.getMonth() + 1).padStart(2, "0");
            const lastDay = new Date(y, now.getMonth() + 1, 0).getDate();
            this.state.dateFrom = `${y}-${m}-01`;
            this.state.dateTo = `${y}-${m}-${lastDay}`;
        } else if (preset === "this_year") {
            this.state.dateFrom = `${y}-01-01`;
            this.state.dateTo = `${y}-12-31`;
        } else if (preset === "last_year") {
            this.state.dateFrom = `${y - 1}-01-01`;
            this.state.dateTo = `${y - 1}-12-31`;
        }
        this.loadReportData();
    }

    toggleAccount(accId) {
        if (this.state.unfoldedAccounts.has(accId)) {
            this.state.unfoldedAccounts.delete(accId);
        } else {
            this.state.unfoldedAccounts.add(accId);
        }
    }

    isAccountUnfolded(accId) {
        return this.state.unfoldedAccounts.has(accId);
    }

    openAccountLines(accountId, accountName) {
        if (!accountId) return;
        this.action.doAction({
            name: accountName || "Journal Items",
            type: "ir.actions.act_window",
            res_model: "account.move.line",
            view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            domain: [
                ["account_id", "=", accountId],
                ["date", "<=", this.state.dateTo],
                ...(this.state.dateFrom ? [["date", ">=", this.state.dateFrom]] : []),
                ...(this.state.targetMove === "posted" ? [["parent_state", "=", "posted"]] : []),
            ],
            target: "current",
        });
    }

    openJournalEntry(moveName) {
        if (!moveName) return;
        this.action.doAction({
            name: `Entry: ${moveName}`,
            type: "ir.actions.act_window",
            res_model: "account.move",
            view_mode: "form",
            domain: [["name", "=", moveName]],
            target: "current",
        });
    }

    async printPdf() {
        const action = await this.orm.call("financial.report.wizard", "create", [{
            report_type: this.state.reportType,
            date_from: this.state.dateFrom,
            date_to: this.state.dateTo,
            target_move: this.state.targetMove,
        }]);
        return this.action.doAction({
            type: "ir.actions.report",
            report_name: "account_enterprise_ce.report_financial_statement_tmpl",
            report_type: "qweb-pdf",
            data: { report_data: this.state.data },
        });
    }

    formatMonetary(amount) {
        if (amount === undefined || amount === null) return "0.00";
        const sym = this.state.data?.currency_symbol || "$";
        const pos = this.state.data?.currency_position || "before";
        const formatted = Number(amount).toLocaleString(undefined, {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        });
        return pos === "before" ? `${sym} ${formatted}` : `${formatted} ${sym}`;
    }
}

registry.category("actions").add("account_financial_report_widget", FinancialReportWidget);
