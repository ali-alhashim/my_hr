# -*- coding: utf-8 -*-
import io
import base64
from datetime import date
from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


class MyHrPayrollBatch(models.Model):
    _name = 'my_hr.payroll.batch'
    _description = 'Payroll Batch'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_from desc'
    _rec_name = 'name'

    name = fields.Char(
        string='Batch Name',
        required=True,
        tracking=True,
        copy=False
    )
    date_from = fields.Date(string='Period Start', required=True, tracking=True)
    date_to = fields.Date(string='Period End', required=True, tracking=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('manager_approve', 'Pending Manager Approval'),
        ('ceo_approve', 'Pending CEO Approval'),
        ('published', 'Published'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True, copy=False)
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        required=True
    )
    payslip_ids = fields.One2many(
        'my_hr.payslip', 'batch_id',
        string='Payslips'
    )
    payslip_count = fields.Integer(
        compute='_compute_payslip_count',
        string='Payslips'
    )
    notes = fields.Text(string='Notes')
    wps_file = fields.Binary(string='WPS File', readonly=True, copy=False)
    wps_filename = fields.Char(string='WPS Filename', readonly=True, copy=False)

    @api.depends('payslip_ids')
    def _compute_payslip_count(self):
        for batch in self:
            batch.payslip_count = len(batch.payslip_ids)

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for batch in self:
            if batch.date_from > batch.date_to:
                raise ValidationError('Period end date must be after start date.')

    # ---- State transitions ----

    def action_submit_manager(self):
        self.ensure_one()
        if self.state != 'draft':
            raise UserError('Only Draft batches can be submitted.')
        if not self.payslip_ids:
            raise UserError('Please generate payslips before submitting.')
        self.state = 'manager_approve'

    def action_manager_approve(self):
        self.ensure_one()
        if self.state != 'manager_approve':
            raise UserError('Batch is not pending manager approval.')
        self.state = 'ceo_approve'

    def action_ceo_approve(self):
        self.ensure_one()
        if self.state != 'ceo_approve':
            raise UserError('Batch is not pending CEO approval.')
        self.state = 'published'

    def action_cancel(self):
        if self.state == 'published':
            raise UserError('Published batches cannot be cancelled.')
        self.state = 'cancelled'

    def action_reset_draft(self):
        if self.state == 'published':
            raise UserError('Published batches cannot be reset to draft.')
        self.state = 'draft'

    # ---- Payslip generation ----

    def action_generate_payslips(self):
        self.ensure_one()
        if self.state != 'draft':
            raise UserError('Payslips can only be generated in Draft state.')

        employees = self.env['hr.employee'].search([
            ('active', '=', True),
            ('company_id', '=', self.company_id.id),
        ])

        # Remove existing draft payslips
        self.payslip_ids.filtered(lambda p: p.state == 'draft').unlink()

        payslips = []
        for emp in employees:
            payslips.append({
                'batch_id': self.id,
                'employee_id': emp.id,
                'date_from': self.date_from,
                'date_to': self.date_to,
                'state': 'draft',
            })
        if payslips:
            created = self.env['my_hr.payslip'].create(payslips)
            created.action_compute()

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Payslips Generated',
                'message': f'{len(payslips)} payslip(s) generated and computed.',
                'type': 'success',
            }
        }

    # ---- WPS Export ----

    def action_export_wps(self):
        self.ensure_one()
        if self.state != 'published':
            raise UserError('Only Published batches can be exported to WPS.')
        wps_content = self._generate_wps_file()
        filename = f"WPS_{self.name.replace(' ', '_')}_{self.date_to}.txt"
        self.write({
            'wps_file': base64.b64encode(wps_content.encode('utf-8')),
            'wps_filename': filename,
        })
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/my_hr.payroll.batch/{self.id}/wps_file/{filename}?download=true',
            'target': 'self',
        }

    def _generate_wps_file(self):
        """
        Generate a fixed-width WPS text file complying with HRSD standards.
        Record Types:
          H - Header
          D - Detail (employee)
          T - Trailer/Footer
        """
        self.ensure_one()
        lines = []
        total_salary = 0.0
        detail_count = 0

        # --- Header Record ---
        # Format: H | Employer ID | File Date | Currency | Reserved
        employer_id = (self.company_id.vat or '0000000000').replace(' ', '').ljust(10)[:10]
        file_date = fields.Date.today().strftime('%Y%m%d')
        currency_code = (self.company_id.currency_id.name or 'SAR').ljust(3)[:3]
        header = (
            f"H"
            f"{employer_id}"
            f"{file_date}"
            f"{currency_code}"
            f"{'':52}"   # Reserved padding
        )
        lines.append(header)

        # --- Detail Records ---
        for slip in self.payslip_ids.filtered(lambda p: p.state == 'confirmed'):
            emp = slip.employee_id
            # Sanitize IBAN: remove spaces, ensure 24 chars (SA IBANs are 24)
            raw_iban = ''
            if emp.bank_account_id and emp.bank_account_id.acc_number:
                raw_iban = emp.bank_account_id.acc_number.replace(' ', '').upper()
            iban = raw_iban[:24].ljust(24)

            emp_id = (emp.id_number or str(emp.id)).replace(' ', '').ljust(15)[:15]
            salary_str = f"{slip.net_salary:015.2f}".replace('.', '').zfill(15)[:15]
            name = (emp.name or '').ljust(40)[:40]
            salary_month = self.date_to.strftime('%Y%m')

            detail = (
                f"D"
                f"{emp_id}"
                f"{iban}"
                f"{salary_str}"
                f"{name}"
                f"{salary_month}"
                f"{'':5}"  # Reserved
            )
            lines.append(detail)
            total_salary += slip.net_salary
            detail_count += 1

        # --- Footer / Trailer Record ---
        total_str = f"{total_salary:015.2f}".replace('.', '').zfill(15)[:15]
        count_str = str(detail_count).zfill(6)[:6]
        footer = (
            f"T"
            f"{count_str}"
            f"{total_str}"
            f"{'':45}"  # Reserved padding
        )
        lines.append(footer)

        return '\r\n'.join(lines)