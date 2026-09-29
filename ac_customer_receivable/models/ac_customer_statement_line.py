from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import float_compare

from .ac_customer_job_payment import PAYMENT_METHODS


class AcCustomerStatementLine(models.Model):
    _name = 'ac.customer.statement.line'
    _description = 'Customer Statement Transaction'
    _order = 'date asc, id asc'

    name = fields.Char(string='Description', required=True)
    date = fields.Date(
        string='Date',
        required=True,
        default=fields.Date.context_today,
        index=True,
    )
    customer_id = fields.Many2one(
        'ac.customer.master',
        string='Customer',
        required=True,
        ondelete='cascade',
        index=True,
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        related='company_id.currency_id',
        store=True,
        readonly=True,
    )
    transaction_type = fields.Selection(
        selection=[
            ('opening', 'Opening Balance'),
            ('receivable', 'Receivable'),
            ('payment', 'Payment'),
            ('payment_revert', 'Payment Reversal'),
            ('refund', 'Refund'),
        ],
        string='Type',
        required=True,
        index=True,
    )
    payment_method = fields.Selection(
        selection=PAYMENT_METHODS,
        string='Payment Method',
    )
    debit = fields.Monetary(
        string='Debit',
        currency_field='currency_id',
        default=0.0,
    )
    credit = fields.Monetary(
        string='Credit',
        currency_field='currency_id',
        default=0.0,
    )
    state = fields.Selection(
        selection=[
            ('posted', 'Posted'),
            ('cancelled', 'Cancelled'),
        ],
        string='Status',
        default='posted',
        required=True,
        index=True,
    )
    job_id = fields.Many2one(
        'ac.customer.job',
        string='Service Engagement',
        ondelete='set null',
        index=True,
    )
    payment_id = fields.Many2one(
        'ac.customer.job.payment',
        string='Payment',
        ondelete='set null',
        index=True,
    )
    refund_id = fields.Many2one(
        'ac.customer.job.refund',
        string='Refund',
        ondelete='set null',
        index=True,
    )
    notes = fields.Char(string='Notes')

    @api.constrains('debit', 'credit')
    def _check_debit_credit(self):
        for line in self:
            rounding = line.currency_id.rounding if line.currency_id else 0.01
            if float_compare(line.debit, 0.0, precision_rounding=rounding) < 0:
                raise UserError(_('Debit amount cannot be negative.'))
            if float_compare(line.credit, 0.0, precision_rounding=rounding) < 0:
                raise UserError(_('Credit amount cannot be negative.'))
            if (
                float_compare(line.debit, 0.0, precision_rounding=rounding) > 0
                and float_compare(line.credit, 0.0, precision_rounding=rounding) > 0
            ):
                raise UserError(_('A statement line cannot have both debit and credit amounts.'))

    def action_cancel(self):
        self.write({'state': 'cancelled'})
        return True
