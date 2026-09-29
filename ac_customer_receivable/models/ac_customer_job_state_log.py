from odoo import _, fields, models
from odoo.exceptions import UserError


class AcCustomerJobStateLog(models.Model):
    _name = 'ac.customer.job.state.log'
    _description = 'Service Engagement Activity Log'
    _order = 'log_date desc, id desc'

    job_id = fields.Many2one(
        'ac.customer.job',
        string='Service Engagement',
        required=True,
        ondelete='cascade',
        index=True,
    )
    user_id = fields.Many2one(
        'res.users',
        string='User',
        required=True,
        default=lambda self: self.env.user,
        readonly=True,
    )
    log_date = fields.Datetime(
        string='Date',
        required=True,
        default=fields.Datetime.now,
        readonly=True,
    )
    log_type = fields.Selection(
        selection=[
            ('state_change', 'State Change'),
            ('field_update', 'Field Update'),
            ('service_add', 'Service Added'),
            ('service_update', 'Service Updated'),
            ('service_remove', 'Service Removed'),
        ],
        string='Type',
        required=True,
        default='state_change',
        readonly=True,
    )
    field_name = fields.Char(string='Field', readonly=True)
    old_value = fields.Text(string='Previous Value', readonly=True)
    new_value = fields.Text(string='New Value', readonly=True)
    from_state = fields.Selection(
        selection=[
            ('not_started', 'Not Started'),
            ('started', 'Started'),
            ('in_progress', 'In Progress'),
            ('done', 'Done'),
            ('declined', 'Declined'),
        ],
        string='From State',
        readonly=True,
    )
    to_state = fields.Selection(
        selection=[
            ('not_started', 'Not Started'),
            ('started', 'Started'),
            ('in_progress', 'In Progress'),
            ('done', 'Done'),
            ('declined', 'Declined'),
        ],
        string='To State',
        readonly=True,
    )
    payment_id = fields.Many2one(
        'ac.customer.job.payment',
        string='Payment',
        readonly=True,
        ondelete='set null',
    )
    has_upi_screenshot = fields.Boolean(
        string='Has UPI Screenshot',
        readonly=True,
        default=False,
    )

    def action_view_upi_screenshot(self):
        self.ensure_one()
        payment = self.payment_id
        if not payment or not payment.upi_screenshot:
            raise UserError(_('No UPI screenshot is attached to this activity log.'))
        return {
            'type': 'ir.actions.act_window',
            'name': _('UPI Screenshot'),
            'res_model': 'ac.customer.job.payment',
            'res_id': payment.id,
            'view_mode': 'form',
            'views': [(self.env.ref(
                'ac_customer_receivable.ac_customer_job_payment_upi_screenshot_view_form'
            ).id, 'form')],
            'target': 'new',
        }
