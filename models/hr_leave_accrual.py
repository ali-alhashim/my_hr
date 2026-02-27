# -*- coding: utf-8 -*-
import logging
from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class HrLeaveAccrual(models.AbstractModel):
    _name = 'hr.leave.accrual'
    _description = 'Leave Accrual Engine'

    @api.model
    def run_daily_accrual(self):
        """
        Daily cron: Add 30/365 days to every active employee's annual leave allocation.
        Only accrues for leave types that have accrual enabled.
        """
        accrual_amount = 30.0 / 365.0  # days to add per day

        # Find annual leave type
        annual_leave = self.env['hr.leave.type'].search([
            ('my_hr_accrual', '=', True),
            ('active', '=', True),
        ])

        if not annual_leave:
            _logger.warning('my_hr: No leave types with accrual enabled. Skipping.')
            return

        employees = self.env['hr.employee'].search([
            ('active', '=', True),
        ])

        for leave_type in annual_leave:
            for emp in employees:
                # Find existing allocation or create one
                allocation = self.env['hr.leave.allocation'].search([
                    ('employee_id', '=', emp.id),
                    ('holiday_status_id', '=', leave_type.id),
                    ('state', '=', 'validate'),
                    ('date_from', '<=', fields.Date.today()),
                    '|',
                    ('date_to', '=', False),
                    ('date_to', '>=', fields.Date.today()),
                ], limit=1)

                if allocation:
                    new_days = (allocation.number_of_days or 0.0) + accrual_amount
                    allocation.sudo().write({'number_of_days': new_days})
                    _logger.info(
                        'Accrued %.4f day(s) for employee %s on leave type %s. New balance: %.4f',
                        accrual_amount, emp.name, leave_type.name, new_days
                    )
                else:
                    _logger.debug(
                        'No validated allocation found for employee %s on leave type %s',
                        emp.name, leave_type.name
                    )


class HrLeaveType(models.Model):
    _inherit = 'hr.leave.type'

    my_hr_accrual = fields.Boolean(
        string='Enable Daily Accrual',
        default=False,
        help='If enabled, days are automatically accrued daily (30 days/year rate).'
    )
    my_hr_affects_balance = fields.Boolean(
        string='Affects Leave Balance',
        default=True,
        help='Uncheck for leave types like Unpaid that should not affect the balance.'
    )