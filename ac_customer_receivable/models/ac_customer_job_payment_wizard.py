from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare

from .ac_customer_job_payment import PAYMENT_METHODS


class AcCustomerJobPaymentWizard(models.TransientModel):
    _name = 'ac.customer.job.payment.wizard'
    _description = 'Record Service Engagement Payment'

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
    amount_total = fields.Monetary(
        string='Grand Total',
        related='job_id.amount_total',
        readonly=True,
        currency_field='currency_id',
    )
    amount_paid = fields.Monetary(
        string='Paid Amount',
        related='job_id.amount_paid',
        readonly=True,
        currency_field='currency_id',
    )
    amount_remaining = fields.Monetary(
        string='Remaining Amount',
        related='job_id.amount_remaining',
        readonly=True,
        currency_field='currency_id',
    )
    payment_scope = fields.Selection(
        selection=[
            ('full', 'Pay Full'),
            ('partial', 'Pay Partial'),
        ],
        string='Payment Option',
        required=True,
        default='full',
    )
    amount = fields.Monetary(
        string='Payment Amount',
        currency_field='currency_id',
    )
    payment_method = fields.Selection(
        selection=PAYMENT_METHODS,
        string='Payment Method',
        required=True,
        default='cash',
    )
    transaction_id = fields.Char(string='Transaction ID')
    cheque_ref = fields.Char(string='Cheque Ref')
    upi_screenshot = fields.Binary(string='UPI Screenshot', attachment=True)
    upi_screenshot_filename = fields.Char(string='Screenshot Filename')

    @api.onchange('payment_scope')
    def _onchange_payment_scope(self):
        if self.payment_scope == 'full':
            self.amount = self.amount_remaining
        elif self.payment_scope == 'partial':
            self.amount = 0.0

    @api.onchange('job_id')
    def _onchange_job_id(self):
        if self.payment_scope == 'full':
            self.amount = self.amount_remaining

    @api.onchange('payment_method')
    def _onchange_payment_method(self):
        if self.payment_method != 'upi':
            self.transaction_id = False
            self.upi_screenshot = False
            self.upi_screenshot_filename = False
        if self.payment_method != 'cheque':
            self.cheque_ref = False

    @api.constrains('amount', 'payment_scope', 'amount_remaining')
    def _check_amount(self):
        for wizard in self:
            rounding = wizard.currency_id.rounding
            if float_compare(wizard.amount, 0.0, precision_rounding=rounding) <= 0:
                raise ValidationError(_('Payment amount must be greater than zero.'))
            if float_compare(wizard.amount, wizard.amount_remaining, precision_rounding=rounding) > 0:
                raise ValidationError(_('Payment amount cannot exceed the remaining amount.'))
            if wizard.payment_scope == 'full' and float_compare(
                wizard.amount, wizard.amount_remaining, precision_rounding=rounding
            ) != 0:
                raise ValidationError(_('Pay Full must use the full remaining amount.'))

    @api.constrains('payment_method', 'transaction_id', 'cheque_ref')
    def _check_payment_reference(self):
        for wizard in self:
            if wizard.payment_method == 'upi' and not wizard.transaction_id:
                raise ValidationError(_('Transaction ID is required for UPI payments.'))
            if wizard.payment_method == 'cheque' and not wizard.cheque_ref:
                raise ValidationError(_('Cheque Ref is required for Cheque payments.'))

    def action_confirm(self):
        self.ensure_one()
        job = self.job_id
        if job.state == 'declined':
            raise UserError(_('Payments cannot be recorded on declined engagements.'))
        if self.amount_remaining <= 0:
            raise UserError(_('This engagement has no remaining balance to pay.'))

        payment_amount = self.amount_remaining if self.payment_scope == 'full' else self.amount
        rounding = self.currency_id.rounding
        if float_compare(payment_amount, 0.0, precision_rounding=rounding) <= 0:
            raise UserError(_('Payment amount must be greater than zero.'))
        if float_compare(payment_amount, self.amount_remaining, precision_rounding=rounding) > 0:
            raise UserError(_('Payment amount cannot exceed the remaining amount.'))

        if self.payment_method == 'upi' and not self.transaction_id:
            raise UserError(_('Transaction ID is required for UPI payments.'))
        if self.payment_method == 'cheque' and not self.cheque_ref:
            raise UserError(_('Cheque Ref is required for Cheque payments.'))

        payment_vals = {
            'job_id': job.id,
            'payment_scope': self.payment_scope,
            'payment_method': self.payment_method,
            'amount': payment_amount,
            'transaction_id': self.transaction_id if self.payment_method == 'upi' else False,
            'cheque_ref': self.cheque_ref if self.payment_method == 'cheque' else False,
        }
        if self.payment_method == 'upi' and self.upi_screenshot:
            payment_vals.update({
                'upi_screenshot': self.upi_screenshot,
                'upi_screenshot_filename': self.upi_screenshot_filename,
            })

        payment = self.env['ac.customer.job.payment'].create(payment_vals)

        method_label = dict(PAYMENT_METHODS).get(self.payment_method, self.payment_method)
        details = '%s - %s' % (payment_amount, method_label)
        if self.payment_method == 'upi' and self.transaction_id:
            details += ' (%s)' % self.transaction_id
        if self.payment_method == 'cheque' and self.cheque_ref:
            details += ' [Ref: %s]' % self.cheque_ref
        if self.payment_method == 'upi' and self.upi_screenshot:
            details += ' [%s]' % _('Screenshot attached')

        job._log_activity(
            'field_update',
            field_label=_('Payment Recorded'),
            new_value=details,
            payment_id=payment.id,
            has_upi_screenshot=bool(self.payment_method == 'upi' and self.upi_screenshot),
        )

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _('Payment of %s has been recorded.') % payment_amount,
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.act_window_close'},
            },
        }
