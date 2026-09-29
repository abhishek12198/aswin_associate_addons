from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare

from .ac_customer_job_payment import PAYMENT_METHODS


class AcCustomerJobRefundWizard(models.TransientModel):
    _name = 'ac.customer.job.refund.wizard'
    _description = 'Request Service Engagement Refund'

    job_id = fields.Many2one(
        'ac.customer.job',
        string='Service Engagement',
        required=True,
        readonly=True,
        ondelete='cascade',
    )
    currency_id = fields.Many2one(
        related='job_id.currency_id',
        readonly=True,
    )
    amount_paid = fields.Monetary(
        string='Paid Amount',
        related='job_id.amount_paid',
        readonly=True,
        currency_field='currency_id',
    )
    amount_refunded = fields.Monetary(
        string='Already Refunded',
        related='job_id.amount_refunded',
        readonly=True,
        currency_field='currency_id',
    )
    amount_refundable = fields.Monetary(
        string='Refundable Amount',
        related='job_id.amount_refundable',
        readonly=True,
        currency_field='currency_id',
    )
    refund_scope = fields.Selection(
        selection=[
            ('full', 'Refund Full'),
            ('partial', 'Refund Partial'),
        ],
        string='Refund Option',
        required=True,
        default='full',
    )
    amount = fields.Monetary(
        string='Refund Amount',
        currency_field='currency_id',
    )
    payment_method = fields.Selection(
        selection=PAYMENT_METHODS,
        string='Refund Method',
        required=True,
        default='cash',
    )
    transaction_id = fields.Char(string='Transaction ID')
    cheque_ref = fields.Char(string='Cheque Ref')
    notes = fields.Text(string='Notes')

    @api.onchange('refund_scope')
    def _onchange_refund_scope(self):
        if self.refund_scope == 'full':
            self.amount = self.amount_refundable
        elif self.refund_scope == 'partial':
            self.amount = 0.0

    @api.onchange('job_id')
    def _onchange_job_id(self):
        if self.refund_scope == 'full':
            self.amount = self.amount_refundable

    @api.onchange('payment_method')
    def _onchange_payment_method(self):
        if self.payment_method != 'upi':
            self.transaction_id = False
        if self.payment_method != 'cheque':
            self.cheque_ref = False

    @api.constrains('amount', 'refund_scope', 'amount_refundable')
    def _check_amount(self):
        for wizard in self:
            rounding = wizard.currency_id.rounding
            if float_compare(wizard.amount, 0.0, precision_rounding=rounding) <= 0:
                raise ValidationError(_('Refund amount must be greater than zero.'))
            if float_compare(wizard.amount, wizard.amount_refundable, precision_rounding=rounding) > 0:
                raise ValidationError(_('Refund amount cannot exceed the refundable amount.'))
            if wizard.refund_scope == 'full' and float_compare(
                wizard.amount, wizard.amount_refundable, precision_rounding=rounding
            ) != 0:
                raise ValidationError(_('Refund Full must use the full refundable amount.'))

    @api.constrains('payment_method', 'transaction_id', 'cheque_ref')
    def _check_payment_reference(self):
        for wizard in self:
            if wizard.payment_method == 'upi' and not wizard.transaction_id:
                raise ValidationError(_('Transaction ID is required for UPI refunds.'))
            if wizard.payment_method == 'cheque' and not wizard.cheque_ref:
                raise ValidationError(_('Cheque Ref is required for Cheque refunds.'))

    def action_confirm(self):
        self.ensure_one()
        job = self.job_id
        if job.state != 'declined':
            raise UserError(_('Refunds can only be requested on declined engagements.'))
        if float_compare(job.amount_refundable, 0.0, precision_rounding=self.currency_id.rounding) <= 0:
            raise UserError(_('There is no refundable payment balance on this engagement.'))

        refund_amount = self.amount_refundable if self.refund_scope == 'full' else self.amount
        rounding = self.currency_id.rounding
        if float_compare(refund_amount, 0.0, precision_rounding=rounding) <= 0:
            raise UserError(_('Refund amount must be greater than zero.'))
        if float_compare(refund_amount, job.amount_refundable, precision_rounding=rounding) > 0:
            raise UserError(_('Refund amount cannot exceed the refundable amount.'))

        if self.payment_method == 'upi' and not self.transaction_id:
            raise UserError(_('Transaction ID is required for UPI refunds.'))
        if self.payment_method == 'cheque' and not self.cheque_ref:
            raise UserError(_('Cheque Ref is required for Cheque refunds.'))

        pending = job.refund_ids.filtered(lambda refund: refund.state == 'waiting_approval')
        if pending:
            raise UserError(_(
                'There is already a refund waiting for approval (%s). '
                'Approve or reject it before requesting another.'
            ) % pending[0].name)

        refund = self.env['ac.customer.job.refund'].create({
            'job_id': job.id,
            'refund_scope': self.refund_scope,
            'payment_method': self.payment_method,
            'amount': refund_amount,
            'transaction_id': self.transaction_id if self.payment_method == 'upi' else False,
            'cheque_ref': self.cheque_ref if self.payment_method == 'cheque' else False,
            'notes': self.notes,
            'state': 'waiting_approval',
        })

        method_label = dict(PAYMENT_METHODS).get(self.payment_method, self.payment_method)
        job._log_activity(
            'field_update',
            field_label=_('Refund Requested'),
            new_value='%(name)s - %(amount)s (%(method)s)' % {
                'name': refund.name,
                'amount': refund_amount,
                'method': method_label,
            },
        )

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Refund Submitted'),
                'message': _(
                    'Refund %(name)s for %(amount)s is waiting for Administrator approval.'
                ) % {'name': refund.name, 'amount': refund_amount},
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.act_window_close'},
            },
        }
