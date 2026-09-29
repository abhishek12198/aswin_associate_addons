# -*- coding: utf-8 -*-
from odoo import http
from odoo.addons.web.controllers.main import Home, Session
from odoo.http import request


class AcBusinessLoginController(Home):
    """Render the business login theme instead of the default Odoo login."""

    @http.route('/web/login', type='http', auth='none', sitemap=False)
    def web_login(self, redirect=None, **kw):
        response = super().web_login(redirect=redirect, **kw)
        if hasattr(response, 'template') and response.template == 'web.login':
            response.template = 'ac_business_login_theme.login'
            company = request.env['res.company'].sudo().search([], order='id', limit=1)
            response.qcontext.update({
                'company_name': company.name if company else 'Company',
                'company_logo_url': '/web/binary/company_logo',
                'favicon_url': (
                    '/web/image/res.company/%d/favicon' % company.id
                    if company and company.favicon
                    else '/web/binary/company_logo'
                ),
            })
        return response


class AcBusinessLogoutController(Session):
    """Redirect logout to the branded login page with a short goodbye state."""

    @http.route('/web/session/logout', type='http', auth='none')
    def logout(self, redirect='/web'):
        request.session.logout(keep_db=True)
        return request.redirect('/web/login?logged_out=1', 303)
