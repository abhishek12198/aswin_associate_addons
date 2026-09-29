from odoo import _, api, fields, models
from odoo.exceptions import UserError


class AcCustomerJobAssignWizard(models.TransientModel):
    _name = 'ac.customer.job.assign.wizard'
    _description = 'Assign Service Engagement'

    job_id = fields.Many2one(
        'ac.customer.job',
        string='Service Engagement',
        required=True,
        readonly=True,
        ondelete='cascade',
    )
    assigned_user_id = fields.Many2one(
        'res.users',
        string='Assignee',
        required=True,
        domain=lambda self: self._get_assignable_user_domain(),
    )

    @api.model
    def _get_assignable_user_domain(self):
        staff_group = self.env.ref('ac_customer_receivable.group_ac_customer_receivable_staff')
        admin_group = self.env.ref('ac_customer_receivable.group_ac_customer_receivable_administrator')
        return [
            ('id', '!=', self.env.uid),
            ('active', '=', True),
            '|',
            ('groups_id', 'in', staff_group.ids),
            ('groups_id', 'in', admin_group.ids),
        ]

    def action_assign(self):
        self.ensure_one()
        if self.job_id.state in ('done', 'declined'):
            raise UserError(_('Cannot assign engagements marked as Done or Declined.'))
        assignee_name = self.assigned_user_id.name
        self.job_id.assigned_user_id = self.assigned_user_id
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _('The service engagement has been assigned to %s.') % assignee_name,
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.act_window_close'},
            },
        }
