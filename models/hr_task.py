# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError, AccessError


class MyHrTask(models.Model):
    _name = 'my.hr.task'
    _description = 'HR Task / Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'
    _rec_name = 'name'

    name = fields.Char(
        string='Subject',
        required=True,
        tracking=True
    )
    description = fields.Html(
        string='Description',
        sanitize=True
    )
    task_type = fields.Selection([
        ('request', 'Request (Employee → Manager)'),
        ('assignment', 'Assignment (Manager → Employee)'),
    ], string='Type', required=True, default='request', tracking=True)

    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        required=True,
        tracking=True,
        default=lambda self: self.env.user.employee_id
    )
    manager_id = fields.Many2one(
        'hr.employee',
        string='Responsible Manager',
        tracking=True
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('assigned', 'Assigned'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('done', 'Done'),
    ], string='Status', default='draft', tracking=True, copy=False)

    deadline = fields.Date(string='Deadline')
    priority = fields.Selection([
        ('0', 'Normal'),
        ('1', 'Important'),
        ('2', 'Urgent'),
    ], default='0', string='Priority')
    company_id = fields.Many2one(
        'res.company',
        default=lambda self: self.env.company
    )

    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        if self.employee_id and self.employee_id.parent_id:
            self.manager_id = self.employee_id.parent_id

    # ---- State actions ----

    def action_submit(self):
        """Employee submits a request to manager."""
        for task in self:
            if task.state != 'draft':
                raise UserError('Only draft tasks can be submitted.')
            if task.task_type == 'request':
                task.state = 'submitted'
                task.message_post(
                    body=f"Task submitted by {task.employee_id.name} for manager review.",
                    subtype_xmlid='mail.mt_note'
                )

    def action_assign(self):
        """Manager creates and assigns a task to an employee."""
        for task in self:
            if task.task_type != 'assignment':
                raise UserError('Only Assignment type tasks can be assigned.')
            if task.state != 'draft':
                raise UserError('Only draft tasks can be assigned.')
            if not task.employee_id:
                raise UserError('Please select an employee to assign.')
            task.state = 'assigned'
            task.message_post(
                body=f"Task assigned to {task.employee_id.name}.",
                subtype_xmlid='mail.mt_note'
            )

    def action_approve(self):
        """Manager approves a request."""
        for task in self:
            if task.state not in ('submitted',):
                raise UserError('Only submitted tasks can be approved.')
            task.state = 'approved'
            task.message_post(
                body=f"Request approved by {self.env.user.name}.",
                subtype_xmlid='mail.mt_note'
            )

    def action_reject(self):
        """Manager rejects a request."""
        for task in self:
            if task.state not in ('submitted',):
                raise UserError('Only submitted tasks can be rejected.')
            task.state = 'rejected'
            task.message_post(
                body=f"Request rejected by {self.env.user.name}.",
                subtype_xmlid='mail.mt_note'
            )

    def action_mark_done(self):
        """Employee marks an assigned task as done."""
        for task in self:
            if task.state not in ('assigned', 'approved'):
                raise UserError('Only assigned or approved tasks can be marked as done.')
            task.state = 'done'
            task.message_post(
                body=f"Task marked as Done by {task.employee_id.name}.",
                subtype_xmlid='mail.mt_note'
            )

    def action_reset_draft(self):
        for task in self:
            if task.state in ('done', 'approved'):
                raise UserError('Completed or approved tasks cannot be reset.')
            task.state = 'draft'