# -*- coding: utf-8 -*-
from odoo import fields, models


class HrAttendance(models.Model):
    _inherit = 'hr.attendance'

    check_in_photo = fields.Binary(
        string='Check-in Photo',
        attachment=True
    )
    check_in_latitude = fields.Float(
        string='Check-in Latitude',
        digits=(10, 7)
    )
    check_in_longitude = fields.Float(
        string='Check-in Longitude',
        digits=(10, 7)
    )
    ip_address = fields.Char(string='IP Address', readonly=True)
    device_info = fields.Char(string='Device / User Agent', readonly=True)
    geofence_id = fields.Many2one(
        'hr.office.geofence',
        string='Matched Office',
        readonly=True
    )