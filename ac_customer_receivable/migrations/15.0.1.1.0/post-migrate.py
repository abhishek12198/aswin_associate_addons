def migrate(cr, version):
    from odoo import SUPERUSER_ID, api
    from odoo.addons.ac_customer_receivable import _backfill_customer_statements

    env = api.Environment(cr, SUPERUSER_ID, {})
    _backfill_customer_statements(env)
