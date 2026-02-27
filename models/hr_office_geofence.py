# -*- coding: utf-8 -*-
import math
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class HrOfficeGeofence(models.Model):
    _name = 'hr.office.geofence'
    _description = 'Office Geofence Configuration'
    _rec_name = 'name'

    name = fields.Char(string='Office Name', required=True)
    latitude = fields.Float(string='Latitude', digits=(10, 7), required=True)
    longitude = fields.Float(string='Longitude', digits=(10, 7), required=True)
    radius = fields.Float(string='Radius (meters)', default=100.0, required=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        'res.company', string='Company',
        default=lambda self: self.env.company,
        required=True
    )
    employee_ids = fields.Many2many(
        'hr.employee',
        'hr_employee_geofence_rel',
        'geofence_id', 'employee_id',
        string='Assigned Employees'
    )

    @api.constrains('radius')
    def _check_radius(self):
        for rec in self:
            if rec.radius <= 0:
                raise ValidationError('Radius must be greater than 0.')

    def check_point_in_radius(self, lat, lon):
        """Use Haversine formula to check if lat/lon is within this geofence radius."""
        self.ensure_one()
        R = 6371000  # Earth radius in meters
        lat1 = math.radians(self.latitude)
        lat2 = math.radians(lat)
        dlat = math.radians(lat - self.latitude)
        dlon = math.radians(lon - self.longitude)

        a = (math.sin(dlat / 2) ** 2 +
             math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        distance = R * c
        return distance <= self.radius