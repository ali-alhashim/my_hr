# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


class MyHrPayslip(models.Model):
    _name = 'my_hr.payslip'
    _description = 'Employee Payslip'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_from desc'
    _rec_name = 'display_name'

    display_name = fields.Char(compute='_compute_display_name', store=True)
    batch_id = fields.Many2one(
        'my_hr.payroll.batch',
        string='Payroll Batch',
        required=True,
        ondelete='cascade'
    )
    employee_id = fields.Many2one(
        'hr.employee', string='Employee',
        required=True, tracking=True
    )
    date_from = fields.Date(string='Period Start', required=True)
    date_to = fields.Date(string='Period End', required=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True)

    # Salary components (computed)
    basic_salary = fields.Monetary(
        string='Basic Salary',
        currency_field='currency_id',
        readonly=True
    )
    housing_allowance = fields.Monetary(
        string='Housing Allowance',
        currency_field='currency_id',
        readonly=True
    )
    transport_allowance = fields.Monetary(
        string='Transport Allowance',
        currency_field='currency_id',
        readonly=True
    )
    gross_salary = fields.Monetary(
        string='Gross Salary',
        currency_field='currency_id',
        readonly=True,
        store=True
    )
    gosi_deduction = fields.Monetary(
        string='GOSI Deduction',
        currency_field='currency_id',
        readonly=True
    )
    attendance_deduction = fields.Monetary(
        string='Attendance Deduction',
        currency_field='currency_id',
        readonly=True
    )
    missing_hours = fields.Float(
        string='Missing Hours',
        readonly=True,
        digits=(10, 2)
    )
    net_salary = fields.Monetary(
        string='Net Salary',
        currency_field='currency_id',
        readonly=True,
        store=True,
        tracking=True
    )
    currency_id = fields.Many2one(
        'res.currency',
        related='batch_id.company_id.currency_id',
        store=True
    )
    notes = fields.Text(string='Notes')

    @api.depends('employee_id', 'date_from', 'date_to')
    def _compute_display_name(self):
        for slip in self:
            if slip.employee_id and slip.date_from:
                slip.display_name = f"{slip.employee_id.name} - {slip.date_from.strftime('%B %Y')}"
            else:
                slip.display_name = 'New Payslip'

    def action_compute(self):
        for slip in self:
            emp = slip.employee_id
            if not emp:
                continue

            basic = emp.basic_salary or 0.0
            housing = emp.housing_allowance or 0.0
            transport = emp.transport_allowance or 0.0
            gross = basic + housing + transport

            # GOSI on basic only
            gosi = basic * (emp.gosi_rate or 0.0) / 100.0

            # Attendance deduction
            attendance_deduction = 0.0
            missing_hours = 0.0

            if not emp.exempt_from_deduction:
                # Calculate expected working hours in period
                # Standard: 8 hours/day, 22 working days/month
                date_from_dt = datetime.combine(slip.date_from, datetime.min.time())
                date_to_dt = datetime.combine(slip.date_to, datetime.max.time())

                attendances = self.env['hr.attendance'].search([
                    ('employee_id', '=', emp.id),
                    ('check_in', '>=', date_from_dt),
                    ('check_in', '<=', date_to_dt),
                ])
                actual_hours = sum(a.worked_hours for a in attendances)

                # Count working days in period (Mon-Fri)
                period_days = (slip.date_to - slip.date_from).days + 1
                working_days = sum(
                    1 for i in range(period_days)
                    if (slip.date_from + timedelta(days=i)).weekday() < 5
                )
                expected_hours = working_days * 8.0
                missing_hours = max(0.0, expected_hours - actual_hours)

                if missing_hours > 0:
                    # Hourly rate = (Gross / 30) / 8
                    hourly_rate = (gross / 30.0) / 8.0
                    attendance_deduction = missing_hours * hourly_rate

            net = gross - gosi - attendance_deduction

            slip.write({
                'basic_salary': basic,
                'housing_allowance': housing,
                'transport_allowance': transport,
                'gross_salary': gross,
                'gosi_deduction': gosi,
                'missing_hours': missing_hours,
                'attendance_deduction': attendance_deduction,
                'net_salary': max(0.0, net),
            })

    def action_confirm(self):
        for slip in self:
            if slip.state != 'draft':
                raise UserError('Only Draft payslips can be confirmed.')
            slip.state = 'confirmed'

    def action_reset_draft(self):
        for slip in self:
            slip.state = 'draft'

    def action_cancel(self):
        for slip in self:
            if slip.state == 'confirmed' and slip.batch_id.state == 'published':
                raise UserError('Cannot cancel a payslip in a published batch.')
            slip.state = 'cancelled'