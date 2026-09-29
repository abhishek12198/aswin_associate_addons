from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import float_compare

from .ac_customer_job_payment import PAYMENT_METHODS


class AcCustomerJobRefund(models.Model):
    _name = 'ac.customer.job.refund'
    _description = 'Service Engagement Refund'
    _order = 'request_date desc, id desc'
    _rec_name = 'name'

    name = fields.Char(
        string='Refund Number',
        copy=False,
        readonly=True,
        index=True,
        default='New',
    )
    job_id = fields.Many2one(
        'ac.customer.job',
        string='Service Engagement',
        required=True,
        ondelete='cascade',
        index=True,
    )
    company_id = fields.Many2one(
        related='job_id.company_id',
        store=True,
        readonly=True,
    )
    currency_id = fields.Many2one(
        related='job_id.currency_id',
        store=True,
        readonly=True,
    )
    customer_id = fields.Many2one(
        related='job_id.customer_id',
        store=True,
        readonly=True,
    )
    request_date = fields.Datetime(
        string='Requested On',
        required=True,
        default=fields.Datetime.now,
        readonly=True,
    )
    refund_scope = fields.Selection(
        selection=[
            ('full', 'Refund Full'),
            ('partial', 'Refund Partial'),
        ],
        string='Refund Type',
        required=True,
        readonly=True,
    )
    payment_method = fields.Selection(
        selection=PAYMENT_METHODS,
        string='Refund Method',
        required=True,
        readonly=True,
    )
    amount = fields.Monetary(
        string='Refund Amount',
        required=True,
        currency_field='currency_id',
        readonly=True,
    )
    transaction_id = fields.Char(string='Transaction ID', readonly=True)
    cheque_ref = fields.Char(string='Cheque Ref', readonly=True)
    notes = fields.Text(string='Notes', readonly=True)
    state = fields.Selection(
        selection=[
            ('waiting_approval', 'Waiting Approval'),
            ('approved', 'Approved'),
            ('rejected', 'Rejected'),
        ],
        string='Status',
        default='waiting_approval',
        required=True,
        readonly=True,
        index=True,
    )
    requested_by = fields.Many2one(
        'res.users',
        string='Requested By',
        required=True,
        default=lambda self: self.env.user,
        readonly=True,
    )
    approved_by = fields.Many2one(
        'res.users',
        string='Approved By',
        readonly=True,
    )
    approved_date = fields.Datetime(string='Approved On', readonly=True)
    rejected_by = fields.Many2one(
        'res.users',
        string='Rejected By',
        readonly=True,
    )
    rejected_date = fields.Datetime(string='Rejected On', readonly=True)
    rejection_reason = fields.Char(string='Rejection Reason', readonly=True)

    @api.model
    def create(self, vals):
        if not vals.get('name') or vals.get('name') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('ac.customer.job.refund') or 'New'
        return super().create(vals)

    def action_approve(self):
        if not self.env.user.has_group(
            'ac_customer_receivable.group_ac_customer_receivable_administrator'
        ):
            raise UserError(_('Only Administrators can approve refunds.'))
        for refund in self:
            if refund.state != 'waiting_approval':
                raise UserError(_('Only refunds waiting for approval can be approved.'))
            if refund.job_id.state != 'declined':
                raise UserError(_('Refunds can only be approved on declined engagements.'))
            refundable = refund.job_id.amount_refundable
            rounding = refund.currency_id.rounding
            if float_compare(refund.amount, refundable, precision_rounding=rounding) > 0:
                raise UserError(_(
                    'Refund amount %(amount)s exceeds the refundable balance %(refundable)s.'
                ) % {'amount': refund.amount, 'refundable': refundable})
            refund.write({
                'state': 'approved',
                'approved_by': self.env.user.id,
                'approved_date': fields.Datetime.now(),
            })
            refund._create_statement_debit()
            refund.job_id._log_activity(
                'field_update',
                field_label=_('Refund Approved'),
                new_value='%(name)s - %(amount)s (%(method)s)' % {
                    'name': refund.name,
                    'amount': refund.amount,
                    'method': dict(PAYMENT_METHODS).get(refund.payment_method, refund.payment_method),
                },
            )
        return True

    def action_reject(self):
        if not self.env.user.has_group(
            'ac_customer_receivable.group_ac_customer_receivable_administrator'
        ):
            raise UserError(_('Only Administrators can reject refunds.'))
        for refund in self:
            if refund.state != 'waiting_approval':
                raise UserError(_('Only refunds waiting for approval can be rejected.'))
            refund.write({
                'state': 'rejected',
                'rejected_by': self.env.user.id,
                'rejected_date': fields.Datetime.now(),
            })
            refund.job_id._log_activity(
                'field_update',
                field_label=_('Refund Rejected'),
                new_value=refund.name,
            )
        return True

    def _create_statement_debit(self):
        """Counter entry for an approved refund (reverse of payment credit)."""
        Statement = self.env['ac.customer.statement.line'].sudo()
        for refund in self:
            if refund.state != 'approved':
                continue
            customer = refund.customer_id
            if not customer:
                continue
            method_label = dict(PAYMENT_METHODS).get(refund.payment_method, refund.payment_method)
            Statement.create({
                'name': _('Refund %s (%s)') % (refund.name, method_label),
                'date': fields.Date.to_date(refund.approved_date) if refund.approved_date else fields.Date.context_today(refund),
                'customer_id': customer.id,
                'company_id': refund.company_id.id,
                'transaction_type': 'refund',
                'payment_method': refund.payment_method,
                'debit': refund.amount,
                'credit': 0.0,
                'job_id': refund.job_id.id,
                'refund_id': refund.id,
                'state': 'posted',
                'notes': refund.notes,
            })
