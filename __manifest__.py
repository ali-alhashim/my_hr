# -*- coding: utf-8 -*-
{
    'name': 'My HR - Complete HR Solution',
    'version': '19.0.1.0.0',
    'category': 'Human Resources',
    'summary': 'Geofenced Attendance, Custom Payroll with WPS, Leave Accrual & Employee Dashboard',
    'description': """
        Complete HR solution for Odoo 19 Community including:
        - Geofenced Attendance with photo capture
        - Custom Payroll Engine with Saudi WPS export
        - Automated Leave Accrual
        - Employee Dashboard with Task/Request Management
    """,
    'author': 'Ali Musa Alhashim',
    'depends': ['hr', 'hr_attendance', 'hr_holidays', 'mail', 'web','base'],
    'data': [
        # Security
        'security/my_hr_groups.xml',
        'security/ir_rules.xml',
        
        # Data
        'data/leave_type_data.xml',
        'data/cron_data.xml',
        # Views
        'views/hr_office_geofence_views.xml',
        'views/hr_employee_views.xml',
        'views/hr_attendance_views.xml',
        'views/payroll_batch_views.xml',
        'views/payslip_views.xml',
        'views/hr_task_views.xml',
        'views/dashboard_views.xml',
        'views/menu_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'my_hr/static/src/css/my_hr.css',
            'my_hr/static/src/xml/systray_checkin.xml',
            'my_hr/static/src/xml/dashboard.xml',
            'my_hr/static/src/js/systray_checkin.js',
            'my_hr/static/src/js/dashboard.js',
        ],
    },
    'post_init_hook': 'post_init_hook',
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}