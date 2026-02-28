# -*- coding: utf-8 -*-
"""
post_init_hook: runs after all models are registered and ir.model records exist.
Creates ACL, record rules, and sets custom fields on existing records.
"""
import logging
_logger = logging.getLogger(__name__)


def post_init_hook(env):
    _set_leave_type_flags(env)
    _create_access_rights(env)
    _create_record_rules(env)


# ── Leave types ────────────────────────────────────────────────────────────────

def _set_leave_type_flags(env):
    """Set my_hr custom fields on leave types created by data XML."""
    mappings = [
        ('my_hr.leave_type_annual', {'my_hr_accrual': True,  'my_hr_affects_balance': True}),
        ('my_hr.leave_type_sick',   {'my_hr_accrual': False, 'my_hr_affects_balance': True}),
        ('my_hr.leave_type_unpaid', {'my_hr_accrual': False, 'my_hr_affects_balance': False}),
    ]
    for xmlid, vals in mappings:
        try:
            rec = env.ref(xmlid, raise_if_not_found=False)
            if rec:
                rec.write(vals)
        except Exception as e:
            _logger.warning('my_hr: could not set leave type flags for %s: %s', xmlid, e)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _get_model(env, model_name):
    return env['ir.model'].search([('model', '=', model_name)], limit=1)


def _already_exists(env, model, name):
    return bool(env['ir.model.data'].search([
        ('module', '=', 'my_hr'), ('name', '=', name), ('model', '=', model)
    ], limit=1))


def _register_xid(env, module_name, model, res_id):
    env['ir.model.data'].create({
        'module': 'my_hr',
        'name': module_name,
        'model': model,
        'res_id': res_id,
    })


# ── Access rights ──────────────────────────────────────────────────────────────

def _create_access_rights(env):
    IrModelAccess = env['ir.model.access']
    g_emp = env.ref('my_hr.group_my_hr_employee')
    g_mgr = env.ref('my_hr.group_my_hr_manager')
    g_pay = env.ref('my_hr.group_my_hr_payroll')

    acls = [
        ('acl_geofence_employee', 'hr.office.geofence', g_emp, True,  False, False, False),
        ('acl_geofence_manager',  'hr.office.geofence', g_mgr, True,  True,  True,  True),
        ('acl_batch_manager',     'my_hr.payroll.batch', g_mgr, True, False, False, False),
        ('acl_batch_payroll',     'my_hr.payroll.batch', g_pay, True, True,  True,  True),
        ('acl_payslip_employee',  'my_hr.payslip',       g_emp, True, False, False, False),
        ('acl_payslip_payroll',   'my_hr.payslip',       g_pay, True, True,  True,  True),
        ('acl_task_employee',     'my.hr.task',          g_emp, True, True,  True,  False),
        ('acl_task_manager',      'my.hr.task',          g_mgr, True, True,  True,  True),
    ]

    for xid, model_name, group, r, w, c, d in acls:
        if _already_exists(env, 'ir.model.access', xid):
            continue
        model_rec = _get_model(env, model_name)
        if not model_rec:
            _logger.warning('my_hr: model %s not found, skipping ACL %s', model_name, xid)
            continue
        rec = IrModelAccess.create({
            'name': f'my_hr {model_name} {group.name}',
            'model_id': model_rec.id,
            'group_id': group.id,
            'perm_read': r, 'perm_write': w,
            'perm_create': c, 'perm_unlink': d,
        })
        _register_xid(env, xid, 'ir.model.access', rec.id)


# ── Record rules ───────────────────────────────────────────────────────────────

def _create_record_rules(env):
    IrRule = env['ir.rule']
    g_emp = env.ref('my_hr.group_my_hr_employee')
    g_mgr = env.ref('my_hr.group_my_hr_manager')
    g_pay = env.ref('my_hr.group_my_hr_payroll')

    rules = [
        (
            'rule_payslip_employee', 'my_hr.payslip',
            "[('employee_id.user_id', '=', user.id)]",
            [g_emp], True, False, False, False,
        ),
        (
            'rule_payslip_manager', 'my_hr.payslip',
            "[('batch_id.company_id', 'in', user.company_ids.ids)]",
            [g_pay], True, True, True, True,
        ),
        (
            'rule_task_employee', 'my.hr.task',
            "['|', ('employee_id.user_id', '=', user.id), ('manager_id.user_id', '=', user.id)]",
            [g_emp], True, True, True, False,
        ),
        (
            'rule_task_manager', 'my.hr.task',
            "[('employee_id.department_id.manager_id.user_id', '=', user.id)]",
            [g_mgr], True, True, True, True,
        ),
        (
            'rule_batch_company', 'my_hr.payroll.batch',
            "[('company_id', 'in', user.company_ids.ids)]",
            [g_pay], True, True, True, True,
        ),
    ]

    for xid, model_name, domain, groups, r, w, c, d in rules:
        if _already_exists(env, 'ir.rule', xid):
            continue
        model_rec = _get_model(env, model_name)
        if not model_rec:
            _logger.warning('my_hr: model %s not found, skipping rule %s', model_name, xid)
            continue
        rec = IrRule.create({
            'name': f'my_hr: {xid}',
            'model_id': model_rec.id,
            'domain_force': domain,
            'groups': [(6, 0, [g.id for g in groups])],
            'perm_read': r, 'perm_write': w,
            'perm_create': c, 'perm_unlink': d,
        })
        _register_xid(env, xid, 'ir.rule', rec.id)