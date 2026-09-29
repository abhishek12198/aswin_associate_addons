# -*- coding: utf-8 -*-
from odoo import api, fields, models

PARAM_KEY = 'ac.business.backend.title'


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    ac_business_backend_title = fields.Char(
        string='Backend App Title',
        help='Optional override for the browser tab title. '
             'Leave empty to use the main company name.',
        config_parameter=PARAM_KEY,
    )

    @api.model
    def get_values(self):
        res = super().get_values()
        res['ac_business_backend_title'] = (
            self.env['ir.config_parameter'].sudo().get_param(PARAM_KEY) or False
        )
        return res
