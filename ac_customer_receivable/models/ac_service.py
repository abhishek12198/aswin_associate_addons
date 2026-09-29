from odoo import fields, models


class AcService(models.Model):
    _name = 'ac.service'
    _description = 'Service'
    _order = 'name'

    name = fields.Char(string='Name', required=True, index=True)
    description = fields.Text(string='Description')
    amount = fields.Monetary(string='Amount', required=True, currency_field='currency_id')
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        required=True,
        default=lambda self: self.env.ref('base.INR', raise_if_not_found=False),
    )
    company_ids = fields.Many2many(
        'res.company',
        'ac_service_company_rel',
        'service_id',
        'company_id',
        string='Companies',
        help='Leave empty to make this service available for all companies.',
    )
    active = fields.Boolean(default=True)
