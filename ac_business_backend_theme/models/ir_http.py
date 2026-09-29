# -*- coding: utf-8 -*-
from odoo import models
from odoo.http import request

PARAM_KEY = 'ac.business.backend.title'


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    def session_info(self):
        result = super().session_info()
        company = request.env.company
        configured_title = request.env['ir.config_parameter'].sudo().get_param(PARAM_KEY)
        result['app_title'] = configured_title or company.name or 'Odoo'
        result['company_name'] = company.name or ''
        result['company_logo_url'] = '/web/binary/company_logo'

        user_companies = result.get('user_companies')
        if user_companies and user_companies.get('allowed_companies'):
            for company_id, company_data in user_companies['allowed_companies'].items():
                company_data['logo_url'] = f'/web/binary/company_logo?company={company_id}'

        return result
