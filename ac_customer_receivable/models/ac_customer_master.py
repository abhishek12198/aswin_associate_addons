from odoo import api, fields, models


class AcCustomerMaster(models.Model):
    _name = 'ac.customer.master'
    _description = 'Customer Master'
    _order = 'name'

    name = fields.Char(string='Name', required=True, index=True)
    customer_company = fields.Char(string='Customer Company')
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
    photo = fields.Image(string='Photo')
    contact_number = fields.Char(string='Contact Number', required=True)
    email = fields.Char(string='Email')
    aadhar_no = fields.Char(string='Aadhar Card No')
    pan_no = fields.Char(string='PAN Card No')
    house_no = fields.Char(string='House No/Flat No')
    street = fields.Char(string='Street Name')
    street2 = fields.Char(string='Street 2')
    city = fields.Char(string='City')
    state_id = fields.Many2one(
        'res.country.state',
        string='State',
        domain="[('country_id', '=', country_id)]",
    )
    country_id = fields.Many2one(
        'res.country',
        string='Country',
        default=lambda self: self.env.ref('base.in', raise_if_not_found=False),
    )
    zip = fields.Char(string='ZIP')
    bank_account_number = fields.Char(string='Account Number')
    bank_ifsc_code = fields.Char(string='IFSC Code')
    job_ids = fields.One2many(
        'ac.customer.job',
        'customer_id',
        string='Service Engagements',
    )
    statement_line_ids = fields.One2many(
        'ac.customer.statement.line',
        'customer_id',
        string='Statement',
    )
    amount_debit = fields.Monetary(
        string='Total Debit',
        compute='_compute_receivable_balance',
        store=True,
        currency_field='currency_id',
    )
    amount_credit = fields.Monetary(
        string='Total Credit',
        compute='_compute_receivable_balance',
        store=True,
        currency_field='currency_id',
    )
    receivable_balance = fields.Monetary(
        string='Receivable',
        compute='_compute_receivable_balance',
        store=True,
        currency_field='currency_id',
        help='Debit - Credit. Positive means customer receivable outstanding; '
             'negative means credit balance (payable).',
    )

    @api.depends(
        'statement_line_ids.debit',
        'statement_line_ids.credit',
        'statement_line_ids.state',
    )
    def _compute_receivable_balance(self):
        for customer in self:
            lines = customer.statement_line_ids.filtered(lambda line: line.state == 'posted')
            debit = sum(lines.mapped('debit'))
            credit = sum(lines.mapped('credit'))
            customer.amount_debit = debit
            customer.amount_credit = credit
            customer.receivable_balance = debit - credit

    @api.model
    def _name_search(self, name='', args=None, operator='ilike', limit=100, name_get_uid=None):
        args = args or []
        if name:
            domain = [
                '|', '|', '|', '|', '|',
                ('name', operator, name),
                ('customer_company', operator, name),
                ('contact_number', operator, name),
                ('email', operator, name),
                ('aadhar_no', operator, name),
                ('pan_no', operator, name),
            ]
            return self._search(domain + args, limit=limit, access_rights_uid=name_get_uid)
        return super()._name_search(
            name, args=args, operator=operator, limit=limit, name_get_uid=name_get_uid,
        )

    @api.onchange('country_id')
    def _onchange_country_id(self):
        if self.state_id and self.state_id.country_id != self.country_id:
            self.state_id = False

    def action_view_statement(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Customer Statement',
            'res_model': 'ac.customer.statement.line',
            'view_mode': 'tree,form',
            'domain': [('customer_id', '=', self.id)],
            'context': {
                'default_customer_id': self.id,
                'default_company_id': self.company_id.id,
            },
        }
