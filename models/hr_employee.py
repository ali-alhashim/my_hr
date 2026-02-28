# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    # Geofence
    allowed_office_ids = fields.Many2many(
        'hr.office.geofence',
        'hr_employee_geofence_rel',
        'employee_id', 'geofence_id',
        string='Allowed Offices'
    )

    # Payroll fields
    basic_salary = fields.Monetary(
        string='Basic Salary',
        currency_field='currency_id',
        groups='hr.group_hr_manager'
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id
    )

    housing_type = fields.Selection([
        ('fixed', 'Fixed Amount'),
        ('percentage', 'Percentage of Basic'),
    ], string='Housing Allowance Type', default='fixed')
    housing_value = fields.Monetary(
        string='Housing Fixed Amount',
        currency_field='currency_id'
    )
    housing_rate = fields.Float(string='Housing % of Basic', digits=(5, 2))

    transport_type = fields.Selection([
        ('fixed', 'Fixed Amount'),
        ('percentage', 'Percentage of Basic'),
    ], string='Transport Allowance Type', default='fixed')
    transport_value = fields.Monetary(
        string='Transport Fixed Amount',
        currency_field='currency_id'
    )
    transport_rate = fields.Float(string='Transport % of Basic', digits=(5, 2))

    gosi_rate = fields.Float(
        string='GOSI Rate (%)',
        digits=(5, 2),
        default=9.75,
        help='GOSI deduction rate on basic salary (employee share)'
    )
    exempt_from_deduction = fields.Boolean(
        string='Exempt from Attendance Deduction',
        default=False
    )
    bank_account_id = fields.Many2one(
        'res.partner.bank',
        string='Bank Account (WPS)',
    )
    

    # Computed salary components
    housing_allowance = fields.Monetary(
        string='Housing Allowance',
        currency_field='currency_id',
        compute='_compute_allowances',
        store=True
    )
    transport_allowance = fields.Monetary(
        string='Transport Allowance',
        currency_field='currency_id',
        compute='_compute_allowances',
        store=True
    )
    gross_salary = fields.Monetary(
        string='Gross Salary',
        currency_field='currency_id',
        compute='_compute_allowances',
        store=True
    )

    @api.depends('basic_salary', 'housing_type', 'housing_value', 'housing_rate',
                 'transport_type', 'transport_value', 'transport_rate')
    def _compute_allowances(self):
        for emp in self:
            housing = 0.0
            if emp.housing_type == 'fixed':
                housing = emp.housing_value or 0.0
            elif emp.housing_type == 'percentage':
                housing = (emp.basic_salary or 0.0) * (emp.housing_rate or 0.0) / 100.0

            transport = 0.0
            if emp.transport_type == 'fixed':
                transport = emp.transport_value or 0.0
            elif emp.transport_type == 'percentage':
                transport = (emp.basic_salary or 0.0) * (emp.transport_rate or 0.0) / 100.0

            emp.housing_allowance = housing
            emp.transport_allowance = transport
            emp.gross_salary = (emp.basic_salary or 0.0) + housing + transport

    @api.constrains('gosi_rate')
    def _check_gosi_rate(self):
        for emp in self:
            if emp.gosi_rate < 0 or emp.gosi_rate > 100:
                raise ValidationError('GOSI rate must be between 0 and 100.')