from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools.misc import format_amount, get_lang

PAYMENT_METHODS = [
    ('cash', 'Cash'),
    ('cheque', 'Cheque'),
    ('upi', 'UPI'),
    ('credit_card', 'Credit Card'),
    ('debit_card', 'Debit Card'),
]


class AcCustomerJobPayment(models.Model):
    _name = 'ac.customer.job.payment'
    _description = 'Service Engagement Payment'
    _order = 'payment_date desc, id desc'
    _rec_name = 'name'

    name = fields.Char(
        string='Receipt Number',
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
    payment_date = fields.Datetime(
        string='Payment Date',
        required=True,
        default=fields.Datetime.now,
        readonly=True,
    )
    payment_method = fields.Selection(
        selection=PAYMENT_METHODS,
        string='Payment Method',
        required=True,
        readonly=True,
    )
    payment_scope = fields.Selection(
        selection=[
            ('full', 'Pay Full'),
            ('partial', 'Pay Partial'),
        ],
        string='Payment Type',
        required=True,
        readonly=True,
    )
    amount = fields.Monetary(
        string='Amount',
        required=True,
        currency_field='currency_id',
        readonly=True,
    )
    transaction_id = fields.Char(string='Transaction ID', readonly=True)
    cheque_ref = fields.Char(string='Cheque Ref', readonly=True)
    upi_screenshot = fields.Binary(
        string='UPI Screenshot',
        attachment=True,
        readonly=True,
    )
    upi_screenshot_filename = fields.Char(
        string='UPI Screenshot Filename',
        readonly=True,
    )
    state = fields.Selection(
        selection=[
            ('posted', 'Posted'),
            ('reverted', 'Reverted'),
        ],
        string='Status',
        default='posted',
        required=True,
        readonly=True,
    )
    recorded_by = fields.Many2one(
        'res.users',
        string='Recorded By',
        required=True,
        default=lambda self: self.env.user,
        readonly=True,
    )
    reverted_by = fields.Many2one(
        'res.users',
        string='Reverted By',
        readonly=True,
    )
    reverted_date = fields.Datetime(string='Reverted Date', readonly=True)

    @api.model
    def create(self, vals):
        if not vals.get('name') or vals.get('name') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('ac.customer.job.payment') or 'New'
        payment = super().create(vals)
        payment._create_statement_credit()
        return payment

    def _create_statement_credit(self):
        Statement = self.env['ac.customer.statement.line'].sudo()
        for payment in self:
            if payment.state != 'posted':
                continue
            customer = payment.job_id.customer_id
            if not customer:
                continue
            method_label = dict(PAYMENT_METHODS).get(payment.payment_method, payment.payment_method)
            Statement.create({
                'name': _('Payment %s (%s)') % (payment.name, method_label),
                'date': fields.Date.to_date(payment.payment_date) if payment.payment_date else fields.Date.context_today(payment),
                'customer_id': customer.id,
                'company_id': payment.company_id.id,
                'transaction_type': 'payment',
                'payment_method': payment.payment_method,
                'debit': 0.0,
                'credit': payment.amount,
                'job_id': payment.job_id.id,
                'payment_id': payment.id,
                'state': 'posted',
            })

    def _cancel_statement_credit(self):
        statements = self.env['ac.customer.statement.line'].sudo().search([
            ('payment_id', 'in', self.ids),
            ('transaction_type', '=', 'payment'),
            ('state', '=', 'posted'),
        ])
        statements.write({'state': 'cancelled'})

    def _get_customer(self):
        self.ensure_one()
        return self.job_id.customer_id

    def _get_customer_address_lines(self):
        self.ensure_one()
        customer = self._get_customer()
        lines = []
        street_line = ', '.join(part for part in [customer.house_no, customer.street, customer.street2] if part)
        if street_line:
            lines.append(street_line)
        city_line = ', '.join(part for part in [
            customer.city,
            customer.state_id.name if customer.state_id else False,
            customer.zip,
        ] if part)
        if city_line:
            lines.append(city_line)
        if customer.country_id:
            lines.append(customer.country_id.name)
        return lines

    def _get_company_address_lines(self):
        self.ensure_one()
        company = self.company_id
        partner = company.partner_id
        lines = []
        street_line = ', '.join(part for part in [partner.street, partner.street2] if part)
        if street_line:
            lines.append(street_line)
        city_line = ', '.join(part for part in [
            partner.city,
            partner.state_id.name if partner.state_id else False,
            partner.zip,
        ] if part)
        if city_line:
            lines.append(city_line)
        if partner.country_id:
            lines.append(partner.country_id.name)
        return lines

    def _get_amount_in_words(self):
        self.ensure_one()
        return self.currency_id.amount_to_text(self.amount) if self.currency_id else ''

    @api.model
    def _format_report_amount(self, amount, currency):
        """Format amounts for PDF reports with INR-safe currency symbol."""
        if not currency:
            return '{:.2f}'.format(amount or 0.0)
        if currency.name == 'INR':
            lang = get_lang(self.env)
            fmt = '%.{0}f'.format(currency.decimal_places)
            formatted_amount = lang.format(
                fmt,
                currency.round(amount or 0.0),
                grouping=True,
                monetary=True,
            )
            symbol = 'Rs.'
            if currency.position == 'before':
                return '%s %s' % (symbol, formatted_amount)
            return '%s %s' % (formatted_amount, symbol)
        return format_amount(self.env, amount or 0.0, currency)

    def action_print_receipt(self):
        self.ensure_one()
        if self.state != 'posted':
            raise UserError(_('Payment receipts can be printed only for posted payments.'))
        if not self.name or self.name == 'New':
            self.write({
                'name': self.env['ir.sequence'].next_by_code('ac.customer.job.payment') or ('RCP/%s' % self.id),
            })
        return self.env.ref('ac_customer_receivable.action_report_ac_payment_receipt').report_action(self)

    def action_revert(self):
        for payment in self:
            if payment.state != 'posted':
                raise UserError(_('Only posted payments can be reverted.'))
            if payment.job_id.state == 'declined':
                raise UserError(_('Payments cannot be reverted on declined engagements.'))
            payment.write({
                'state': 'reverted',
                'reverted_by': self.env.user.id,
                'reverted_date': fields.Datetime.now(),
            })
            payment._cancel_statement_credit()
            payment.job_id._log_activity(
                'field_update',
                field_label=_('Payment Reverted'),
                old_value='%(amount)s (%(method)s on %(date)s)' % {
                    'amount': payment.amount,
                    'method': dict(PAYMENT_METHODS).get(payment.payment_method, payment.payment_method),
                    'date': fields.Datetime.to_string(payment.payment_date),
                },
                new_value=_('Reverted'),
            )
        return True
