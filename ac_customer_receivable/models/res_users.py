from datetime import timedelta
import secrets
import string

from odoo import _, api, fields, models
from odoo.exceptions import AccessError
from odoo.osv import expression

AC_TEMP_PASSWORD_TTL_MINUTES = 10
AC_SUPER_ADMIN_IDS = (1, 2)


class ResUsers(models.Model):
    _inherit = 'res.users'

    ac_access_level = fields.Selection(
        selection=[
            ('staff', 'Staff'),
            ('administrator', 'Administrator'),
        ],
        string='Module Access',
        compute='_compute_ac_access_level',
        inverse='_inverse_ac_access_level',
        store=True,
        default='staff',
    )
    ac_temp_password = fields.Char(
        string='Temporary Password',
        copy=False,
        groups='ac_customer_receivable.group_ac_customer_receivable_administrator',
    )
    ac_temp_password_expiry = fields.Datetime(
        string='Temporary Password Expiry',
        copy=False,
        groups='ac_customer_receivable.group_ac_customer_receivable_administrator',
    )
    ac_show_temp_password = fields.Boolean(
        string='Show Temporary Password',
        compute='_compute_ac_temp_password_display',
    )
    ac_temp_password_display = fields.Char(
        string='Generated Password',
        compute='_compute_ac_temp_password_display',
    )
    ac_can_manage_administrators = fields.Boolean(
        string='Can Manage Administrators',
        compute='_compute_ac_can_manage_administrators',
    )

    @api.model
    def _ac_is_super_admin(self):
        return self.env.user.id in AC_SUPER_ADMIN_IDS

    @api.depends_context('uid')
    def _compute_ac_can_manage_administrators(self):
        can_manage = self._ac_is_super_admin()
        for user in self:
            user.ac_can_manage_administrators = can_manage

    @api.model
    def _generate_ac_password(self, length=12):
        alphabet = string.ascii_letters + string.digits + '!@#$%&*'
        return ''.join(secrets.choice(alphabet) for _ in range(length))

    @api.model
    def _ac_temp_password_expiry(self):
        return fields.Datetime.now() + timedelta(minutes=AC_TEMP_PASSWORD_TTL_MINUTES)

    @api.depends('ac_temp_password', 'ac_temp_password_expiry')
    def _compute_ac_temp_password_display(self):
        now = fields.Datetime.now()
        for user in self:
            if user.ac_temp_password and user.ac_temp_password_expiry and user.ac_temp_password_expiry > now:
                user.ac_show_temp_password = True
                user.ac_temp_password_display = user.ac_temp_password
            else:
                user.ac_show_temp_password = False
                user.ac_temp_password_display = False

    def _set_ac_temp_password(self, password):
        self.write({
            'password': password,
            'ac_temp_password': password,
            'ac_temp_password_expiry': self._ac_temp_password_expiry(),
        })

    @api.model
    def _cron_clear_expired_ac_temp_passwords(self):
        now = fields.Datetime.now()
        expired_users = self.search([
            ('ac_temp_password', '!=', False),
            ('ac_temp_password_expiry', '<=', now),
        ])
        expired_users.write({
            'ac_temp_password': False,
            'ac_temp_password_expiry': False,
        })

    @api.depends('groups_id')
    def _compute_ac_access_level(self):
        admin_group = self.env.ref('ac_customer_receivable.group_ac_customer_receivable_administrator')
        for user in self:
            user.ac_access_level = 'administrator' if admin_group in user.groups_id else 'staff'

    def _inverse_ac_access_level(self):
        self._apply_ac_user_group_policy()

    def _ac_default_groups_for_access_level(self, access_level):
        """Return groups for AC-managed users (internal + staff/admin)."""
        staff_group = self.env.ref('ac_customer_receivable.group_ac_customer_receivable_staff')
        admin_group = self.env.ref('ac_customer_receivable.group_ac_customer_receivable_administrator')
        internal_group = self.env.ref('base.group_user')
        groups = internal_group
        if access_level == 'administrator':
            groups |= admin_group
        else:
            groups |= staff_group
        return groups

    def _ac_check_can_manage_administrators(self, access_level):
        if access_level == 'administrator' and not self._ac_is_super_admin():
            raise AccessError(_(
                'Only super administrators can create or manage Administrator users.'
            ))

    def _apply_ac_user_group_policy(self):
        multi_company_group = self.env.ref('base.group_multi_company', raise_if_not_found=False)
        for user in self:
            groups = self._ac_default_groups_for_access_level(user.ac_access_level)
            if multi_company_group and len(user.company_ids) > 1:
                groups |= multi_company_group
            user.sudo().write({'groups_id': [(6, 0, groups.ids)]})

    @api.model
    def _ac_users_domain(self):
        """Domain for AC Users menu: hide Administrators unless super admin."""
        staff_group = self.env.ref('ac_customer_receivable.group_ac_customer_receivable_staff')
        admin_group = self.env.ref('ac_customer_receivable.group_ac_customer_receivable_administrator')
        if self._ac_is_super_admin():
            return [
                '|',
                ('groups_id', 'in', [staff_group.id]),
                ('groups_id', 'in', [admin_group.id]),
            ]
        return [
            '|',
            ('id', '=', self.env.user.id),
            '&',
            ('groups_id', 'in', [staff_group.id]),
            ('groups_id', 'not in', [admin_group.id]),
        ]

    @api.model
    def _search(self, args, offset=0, limit=None, order=None, count=False, access_rights_uid=None):
        if self.env.context.get('ac_customer_receivable_user_management'):
            args = expression.AND([args or [], self._ac_users_domain()])
        return super()._search(
            args, offset=offset, limit=limit, order=order, count=count,
            access_rights_uid=access_rights_uid,
        )

    @api.model_create_multi
    def create(self, vals_list):
        ac_mgmt = self.env.context.get('ac_customer_receivable_user_management')
        if ac_mgmt:
            for vals in vals_list:
                vals.setdefault('ac_access_level', 'staff')
                self._ac_check_can_manage_administrators(vals.get('ac_access_level', 'staff'))
                if vals.get('login') and not vals.get('email'):
                    vals['email'] = vals['login']
                if not vals.get('password'):
                    temp_password = self._generate_ac_password()
                    vals['password'] = temp_password
                    vals['ac_temp_password'] = temp_password
                    vals['ac_temp_password_expiry'] = self._ac_temp_password_expiry()
                # Assign AC groups before insert so the AC users record rule allows create/read.
                groups = self._ac_default_groups_for_access_level(vals.get('ac_access_level', 'staff'))
                vals['groups_id'] = [(6, 0, groups.ids)]
        create_self = self.sudo() if ac_mgmt else self
        users = super(ResUsers, create_self).create(vals_list)
        if ac_mgmt:
            users.sudo()._apply_ac_user_group_policy()
        return users

    def write(self, vals):
        ac_mgmt = self.env.context.get('ac_customer_receivable_user_management')
        if ac_mgmt:
            if 'ac_access_level' in vals:
                self._ac_check_can_manage_administrators(vals.get('ac_access_level'))
            if vals.get('login') and not vals.get('email'):
                vals['email'] = vals['login']
            write_self = self.sudo()
        else:
            write_self = self
        res = super(ResUsers, write_self).write(vals)
        if ac_mgmt and (
            'ac_access_level' in vals or 'company_ids' in vals
        ):
            self.sudo()._apply_ac_user_group_policy()
        return res

    def action_ac_change_password(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Generate New Password'),
            'res_model': 'ac.customer.receivable.change.password.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_user_id': self.id},
        }
