from odoo import _, fields, models


class AcCustomerReceivableChangePasswordWizard(models.TransientModel):
    _name = 'ac.customer.receivable.change.password.wizard'
    _description = 'Change User Password'

    user_id = fields.Many2one(
        'res.users',
        string='User',
        required=True,
        readonly=True,
        ondelete='cascade',
    )

    def action_generate_password(self):
        self.ensure_one()
        temp_password = self.env['res.users']._generate_ac_password()
        self.user_id._set_ac_temp_password(temp_password)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _(
                    'A new password has been generated. Copy it from the user form now. '
                    'It will disappear automatically after 10 minutes.'
                ),
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.act_window_close'},
            },
        }
