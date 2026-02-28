# -*- coding: utf-8 -*-
import logging
from odoo import api, fields, models

_logger = logging.getLogger(__name__)


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

    @api.model
    def run_daily_accrual(self):
        """
        Daily cron entry point: called as model.run_daily_accrual()
        on hr.leave.type.
        Adds 30/365 days to every active employee's validated annual allocation.
        """
        accrual_amount = 30.0 / 365.0

        accrual_types = self.search([
            ('my_hr_accrual', '=', True),
            ('active', '=', True),
        ])

        if not accrual_types:
            _logger.info('my_hr accrual: no leave types with accrual enabled.')
            return

        employees = self.env['hr.employee'].search([('active', '=', True)])
        today = fields.Date.today()

        for leave_type in accrual_types:
            for emp in employees:
                allocation = self.env['hr.leave.allocation'].search([
                    ('employee_id', '=', emp.id),
                    ('holiday_status_id', '=', leave_type.id),
                    ('state', '=', 'validate'),
                    ('date_from', '<=', today),
                    '|',
                    ('date_to', '=', False),
                    ('date_to', '>=', today),
                ], limit=1)

                if allocation:
                    new_days = (allocation.number_of_days or 0.0) + accrual_amount
                    allocation.sudo().write({'number_of_days': new_days})
                    _logger.debug(
                        'Accrued %.4f day for %s on %s. New total: %.4f',
                        accrual_amount, emp.name, leave_type.name, new_days
                    )