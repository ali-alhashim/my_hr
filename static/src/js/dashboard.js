/** @odoo-module **/

import { Component, useState, onMounted } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

/**
 * Build a calendar for the specified year and month
 * highlighting events passed as [{date: 'YYYY-MM-DD', type: ..., label: ...}]
 */
function buildCalendarData(events, year, month) {
    const firstDay = new Date(year, month, 1).getDay(); // 0=Sun
    const daysInMonth = new Date(year, month + 1, 0).getDate();
    const today = new Date();

    const eventMap = {};
    (events || []).forEach((ev) => {
        const evDate = new Date(ev.date + 'T00:00:00');
        const evYear = evDate.getFullYear();
        const evMonth = evDate.getMonth();
        const evDay = evDate.getDate();
        
        // Only include events for this month/year
        if (evYear === year && evMonth === month) {
            if (!eventMap[evDay]) eventMap[evDay] = [];
            eventMap[evDay].push(ev);
        }
    });

    const isToday = year === today.getFullYear() && month === today.getMonth();
    
    return { year, month, firstDay, daysInMonth, eventMap, today: isToday ? today.getDate() : -1 };
}

class MyHrDashboard extends Component {
    static template = "my_hr.Dashboard";
    // actions pass these standard props; declare so Owl won't complain
    static props = [
        'action',
        'actionId',
        'updateActionState',
        'className',
    ];

    setup() {
        const today = new Date();
        this.state = useState({
            loading: true,
            error: null,
            employee: {
                name: "",
                badge_id: "N/A",
                department: "N/A",
                department_manager: "N/A",
                job_title: "N/A",
            },
            employeeName: "",
            leaveBalance: 0,
            nextPayDate: "N/A",
            totalHours: 0,
            payslips: [],
            calendar: null,
            calendarEvents: [],
            calendarYear: today.getFullYear(),
            calendarMonth: today.getMonth(),
        });

        onMounted(() => this._loadData());
    }

    async _loadData() {
        this.state.loading = true;
        this.state.error = null;
        try {
            // use fetch directly since client actions don't have service injection
            const response = await fetch("/my_hr/dashboard/data", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRF-Token": this._getCsrfToken(),
                },
                body: JSON.stringify({}),
            });
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            const result = await response.json();
            // unwrap Odoo jsonrpc response if present
            const data = result.result || result;
            if (data.success) {
                // Update employee info
                if (data.employee) {
                    this.state.employee = data.employee;
                }
                
                this.state.employeeName = data.employee_name || "";
                this.state.leaveBalance = Math.round((data.leave_balance || 0) * 100) / 100;
                this.state.nextPayDate = data.next_pay_date || "N/A";
                this.state.totalHours = data.total_hours || 0;
                this.state.payslips = data.payslips || [];
                this.state.calendarEvents = data.calendar_events || [];
                this._updateCalendar();
            } else {
                this.state.error = data.error || _t("Could not load dashboard data.");
            }
        } catch (e) {
            console.error('dashboard load error', e);
            this.state.error = _t("Failed to connect. Please refresh.");
        } finally {
            this.state.loading = false;
        }
    }

    _updateCalendar() {
        this.state.calendar = buildCalendarData(
            this.state.calendarEvents,
            this.state.calendarYear,
            this.state.calendarMonth
        );
    }

    previousMonth() {
        if (this.state.calendarMonth === 0) {
            this.state.calendarYear -= 1;
            this.state.calendarMonth = 11;
        } else {
            this.state.calendarMonth -= 1;
        }
        this._updateCalendar();
    }

    nextMonth() {
        if (this.state.calendarMonth === 11) {
            this.state.calendarYear += 1;
            this.state.calendarMonth = 0;
        } else {
            this.state.calendarMonth += 1;
        }
        this._updateCalendar();
    }

    getMonthYearDisplay() {
        const monthNames = [
            'January', 'February', 'March', 'April', 'May', 'June',
            'July', 'August', 'September', 'October', 'November', 'December'
        ];
        return `${monthNames[this.state.calendarMonth]} ${this.state.calendarYear}`;
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
        // Note: Direct action dispatch not available in client action context
        // User can open payslips from the Payslips menu instead
        console.log("Payslip navigation would go to", payslipId);
    }

    openMyRequests() {
        // Note: Direct action dispatch not available in client action context
        // User can access requests from the My Requests menu instead
        console.log("Would navigate to My Requests");
    }

    // lazy service getters
    get rpc() {
        return this.env.services.rpc;
    }
    get notification() {
        return this.env.services.notification;
    }
    get action() {
        return this.env.services.action;
    }

    formatCurrency(amount, symbol) {
        return `${symbol || ""}${(amount || 0).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
    }

    _getCsrfToken() {
        // Extract CSRF token from DOM or cookie
        const token = document.querySelector('input[name="csrf_token"]')?.value ||
                      document.cookie.split('; ').find(row => row.startsWith('csrf_token='))?.split('=')[1];
        return token || '';
    }
}

// Register the client action
registry.category("actions").add("my_hr_dashboard", MyHrDashboard);

export { MyHrDashboard };