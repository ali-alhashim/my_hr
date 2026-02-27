# -*- coding: utf-8 -*-
import logging
from datetime import date, datetime
from odoo import http, fields
from odoo.http import request

_logger = logging.getLogger(__name__)


class DashboardController(http.Controller):

    @http.route(
        '/my_hr/dashboard/data',
        type='json',
        auth='user',
        methods=['POST'],
        csrf=True,
    )
    def get_dashboard_data(self, **kwargs):
        """Return KPI and calendar data for the Employee Dashboard."""
        try:
            uid = request.env.uid
            employee = request.env['hr.employee'].search(
                [('user_id', '=', uid)], limit=1
            )
            if not employee:
                return {'error': 'No employee linked to your account.'}

            today = date.today()
            month_start = today.replace(day=1)

            # --- Leave Balance ---
            annual_leave = request.env['hr.leave.type'].search(
                [('my_hr_accrual', '=', True)], limit=1
            )
            leave_balance = 0.0
            if annual_leave:
                allocation = request.env['hr.leave.allocation'].search([
                    ('employee_id', '=', employee.id),
                    ('holiday_status_id', '=', annual_leave.id),
                    ('state', '=', 'validate'),
                ], limit=1, order='id desc')
                if allocation:
                    leave_balance = allocation.number_of_days or 0.0

            # --- Next Pay Date ---
            # Find latest published batch that includes this month
            next_batch = request.env['my_hr.payroll.batch'].search([
                ('state', '=', 'published'),
                ('date_to', '>=', today.strftime('%Y-%m-%d')),
            ], order='date_to asc', limit=1)
            next_pay_date = next_batch.date_to.strftime('%d %b %Y') if next_batch else 'N/A'

            # --- Hours Worked This Month ---
            attendances = request.env['hr.attendance'].search([
                ('employee_id', '=', employee.id),
                ('check_in', '>=', datetime.combine(month_start, datetime.min.time())),
            ])
            total_hours = round(sum(a.worked_hours for a in attendances), 2)

            # --- Calendar Events ---
            calendar_events = []
            for att in attendances:
                calendar_events.append({
                    'type': 'attendance',
                    'date': att.check_in.strftime('%Y-%m-%d'),
                    'check_in': att.check_in.strftime('%H:%M'),
                    'check_out': att.check_out.strftime('%H:%M') if att.check_out else None,
                    'hours': round(att.worked_hours, 2),
                })

            # Public holidays (global leaves)
            public_holidays = request.env['hr.leave.public.holiday'].search(
                [('active', '=', True)]
            ) if 'hr.leave.public.holiday' in request.env else []
            # Fallback: use hr.leave type
            leaves_off = request.env['hr.leave'].search([
                ('employee_id', '=', employee.id),
                ('state', '=', 'validate'),
                ('date_from', '>=', datetime.combine(month_start, datetime.min.time())),
            ])
            for leave in leaves_off:
                calendar_events.append({
                    'type': 'leave',
                    'date': leave.date_from.strftime('%Y-%m-%d'),
                    'label': leave.holiday_status_id.name or 'Time Off',
                })

            # --- Recent Payslips ---
            payslips = request.env['my_hr.payslip'].search([
                ('employee_id', '=', employee.id),
                ('state', '=', 'confirmed'),
            ], order='date_from desc', limit=12)
            payslip_list = [{
                'id': p.id,
                'name': p.display_name,
                'date': p.date_from.strftime('%B %Y'),
                'net_salary': p.net_salary,
                'currency': p.currency_id.symbol or '',
            } for p in payslips]

            return {
                'success': True,
                'employee_name': employee.name,
                'leave_balance': leave_balance,
                'next_pay_date': next_pay_date,
                'total_hours': total_hours,
                'calendar_events': calendar_events,
                'payslips': payslip_list,
            }
        except Exception as e:
            _logger.exception('Dashboard data error: %s', e)
            return {'success': False, 'error': str(e)}