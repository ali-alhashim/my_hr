# -*- coding: utf-8 -*-
import base64
import logging
from datetime import datetime

from odoo import http, fields
from odoo.http import request
from odoo.exceptions import AccessError

_logger = logging.getLogger(__name__)


class AttendanceController(http.Controller):

    @http.route(
        '/my_hr/attendance/check',
        type='json',
        auth='user',
        methods=['POST'],
        csrf=True,
    )
    def check_in_out(self, **kwargs):
        """
        Endpoint called by the Systray button.
        Expected JSON payload:
          - latitude (float)
          - longitude (float)
          - photo (str, base64 webp image)
          - user_agent (str)
        """
        try:
            latitude = float(kwargs.get('latitude', 0))
            longitude = float(kwargs.get('longitude', 0))
            photo_b64 = kwargs.get('photo', '')
            user_agent = kwargs.get('user_agent', '')[:255]
            ip_address = request.httprequest.remote_addr or ''

            employee = request.env['hr.employee'].search(
                [('user_id', '=', request.env.uid)], limit=1
            )
            if not employee:
                return {'success': False, 'error': 'No employee linked to your user account.'}

            # Geofence validation
            matched_office = None
            allowed_offices = employee.allowed_office_ids
            if allowed_offices:
                for office in allowed_offices:
                    if office.check_point_in_radius(latitude, longitude):
                        matched_office = office
                        break
                if not matched_office:
                    return {
                        'success': False,
                        'error': 'You are outside the allowed office area. Check-in denied.',
                    }

            # Determine check-in or check-out
            last_attendance = request.env['hr.attendance'].search(
                [('employee_id', '=', employee.id), ('check_out', '=', False)],
                order='check_in desc',
                limit=1
            )

            now = fields.Datetime.now()
            attendance_vals = {
                'employee_id': employee.id,
                'check_in_latitude': latitude,
                'check_in_longitude': longitude,
                'ip_address': ip_address,
                'device_info': user_agent,
                'geofence_id': matched_office.id if matched_office else False,
            }

            if last_attendance:
                # Check out
                last_attendance.write({'check_out': now})
                action = 'check_out'
            else:
                # Check in
                attendance_vals['check_in'] = now
                if photo_b64:
                    # Validate it's a proper base64 string
                    try:
                        base64.b64decode(photo_b64)
                        attendance_vals['check_in_photo'] = photo_b64
                    except Exception:
                        _logger.warning('Invalid photo data received from user %s', request.env.uid)
                request.env['hr.attendance'].create(attendance_vals)
                action = 'check_in'

            return {
                'success': True,
                'action': action,
                'employee_name': employee.name,
                'timestamp': now.strftime('%Y-%m-%d %H:%M:%S'),
            }

        except Exception as e:
            _logger.exception('Error processing attendance check-in/out: %s', str(e))
            return {'success': False, 'error': str(e)}

    @http.route(
        '/my_hr/attendance/status',
        type='json',
        auth='user',
        methods=['POST'],
        csrf=True,
    )
    def get_status(self, **kwargs):
        """Return current check-in status for the logged-in employee."""
        try:
            employee = request.env['hr.employee'].search(
                [('user_id', '=', request.env.uid)], limit=1
            )
            if not employee:
                return {'checked_in': False}

            last = request.env['hr.attendance'].search(
                [('employee_id', '=', employee.id), ('check_out', '=', False)],
                order='check_in desc',
                limit=1
            )
            return {
                'checked_in': bool(last),
                'employee_name': employee.name,
                'check_in_time': last.check_in.strftime('%H:%M') if last else None,
            }
        except Exception as e:
            return {'checked_in': False, 'error': str(e)}