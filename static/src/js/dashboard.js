/** @odoo-module **/

import { Component, useState, onMounted } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

/**
 * Build a simple inline SVG calendar for the current month
 * highlighting events passed as [{date: 'YYYY-MM-DD', type: ..., label: ...}]
 */
function buildCalendarData(events) {
    const today = new Date();
    const year = today.getFullYear();
    const month = today.getMonth();
    const firstDay = new Date(year, month, 1).getDay(); // 0=Sun
    const daysInMonth = new Date(year, month + 1, 0).getDate();

    const eventMap = {};
    (events || []).forEach((ev) => {
        const d = ev.date ? parseInt(ev.date.split("-")[2], 10) : null;
        if (d) {
            if (!eventMap[d]) eventMap[d] = [];
            eventMap[d].push(ev);
        }
    });

    return { year, month, firstDay, daysInMonth, eventMap, today: today.getDate() };
}

class MyHrDashboard extends Component {
    static template = "my_hr.Dashboard";
    static props = {};

    setup() {
        this.rpc = useService("rpc");
        this.notification = useService("notification");
        this.action = useService("action");

        this.state = useState({
            loading: true,
            error: null,
            employeeName: "",
            leaveBalance: 0,
            nextPayDate: "N/A",
            totalHours: 0,
            payslips: [],
            calendar: null,
            calendarEvents: [],
        });

        onMounted(() => this._loadData());
    }

    async _loadData() {
        this.state.loading = true;
        this.state.error = null;
        try {
            const data = await this.rpc("/my_hr/dashboard/data", {});
            if (data.success) {
                this.state.employeeName = data.employee_name || "";
                this.state.leaveBalance = Math.round((data.leave_balance || 0) * 100) / 100;
                this.state.nextPayDate = data.next_pay_date || "N/A";
                this.state.totalHours = data.total_hours || 0;
                this.state.payslips = data.payslips || [];
                this.state.calendarEvents = data.calendar_events || [];
                this.state.calendar = buildCalendarData(data.calendar_events || []);
            } else {
                this.state.error = data.error || _t("Could not load dashboard data.");
            }
        } catch (e) {
            this.state.error = _t("Failed to connect. Please refresh.");
        } finally {
            this.state.loading = false;
        }
    }

    getCalendarDays() {
        if (!this.state.calendar) return [];
        const { firstDay, daysInMonth, eventMap, today } = this.state.calendar;
        const days = [];
        // Pad start
        for (let i = 0; i < firstDay; i++) {
            days.push({ day: null });
        }
        for (let d = 1; d <= daysInMonth; d++) {
            const events = eventMap[d] || [];
            days.push({
                day: d,
                isToday: d === today,
                hasAttendance: events.some((e) => e.type === "attendance"),
                hasLeave: events.some((e) => e.type === "leave"),
                events,
            });
        }
        return days;
    }

    openPayslip(payslipId) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "my_hr.payslip",
            res_id: payslipId,
            views: [[false, "form"]],
            target: "current",
        });
    }

    openMyRequests() {
        this.action.doAction("my_hr.action_hr_task_my");
    }

    formatCurrency(amount, symbol) {
        return `${symbol || ""}${(amount || 0).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
    }
}

// Register the client action
registry.category("actions").add("my_hr_dashboard", MyHrDashboard);

export { MyHrDashboard };