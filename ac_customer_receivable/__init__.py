from . import models


def _backfill_customer_statements(env):
    """Sync existing engagements and payments into customer statements."""
    jobs = env['ac.customer.job'].search([])
    jobs._sync_receivable_statement()

    Payment = env['ac.customer.job.payment']
    Statement = env['ac.customer.statement.line']
    posted_payments = Payment.search([('state', '=', 'posted')])
    for payment in posted_payments:
        exists = Statement.search_count([
            ('payment_id', '=', payment.id),
            ('transaction_type', '=', 'payment'),
            ('state', '=', 'posted'),
        ])
        if not exists:
            payment._create_statement_credit()


def post_init_hook(cr, registry):
    from odoo import SUPERUSER_ID, api
    env = api.Environment(cr, SUPERUSER_ID, {})
    _backfill_customer_statements(env)
