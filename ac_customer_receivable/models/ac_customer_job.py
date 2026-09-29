from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import float_compare, float_is_zero

FROZEN_STATES = ('done', 'declined')

JOB_TRACKED_FIELDS = {
    'company_id': 'Company',
    'customer_id': 'Customer',
    'assigned_user_id': 'Assigned To',
    'active': 'Active',
    'job_start_date': 'Job Start Date',
    'job_end_date': 'Job End Date',
}

CUSTOMER_FIELD_MAP = {
    'customer_name': 'name',
    'customer_company': 'customer_company',
    'customer_photo': 'photo',
    'customer_contact_number': 'contact_number',
    'customer_email': 'email',
    'customer_aadhar_no': 'aadhar_no',
    'customer_pan_no': 'pan_no',
    'customer_house_no': 'house_no',
    'customer_street': 'street',
    'customer_street2': 'street2',
    'customer_city': 'city',
    'customer_state_id': 'state_id',
    'customer_country_id': 'country_id',
    'customer_zip': 'zip',
    'customer_bank_account_number': 'bank_account_number',
    'customer_bank_ifsc_code': 'bank_ifsc_code',
}


class AcCustomerJob(models.Model):
    _name = 'ac.customer.job'
    _description = 'Service Engagement'
    _order = 'name'

    name = fields.Char(
        string='Service Engagement Reference',
        required=True,
        copy=False,
        readonly=True,
        default='New',
    )
    active = fields.Boolean(default=True)
    state = fields.Selection(
        selection=[
            ('not_started', 'Not Started'),
            ('started', 'Started'),
            ('in_progress', 'In Progress'),
            ('done', 'Done'),
            ('declined', 'Declined'),
        ],
        string='State',
        default='not_started',
        required=True,
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
        string='Company Currency',
        related='company_id.currency_id',
        store=True,
        readonly=True,
    )
    customer_id = fields.Many2one(
        'ac.customer.master',
        string='Customer',
        required=True,
        ondelete='restrict',
    )
    created_date = fields.Datetime(
        string='Created Date',
        related='create_date',
        store=True,
        readonly=True,
    )
    created_by = fields.Many2one(
        'res.users',
        string='Created By',
        related='create_uid',
        store=True,
        readonly=True,
    )
    assigned_user_id = fields.Many2one(
        'res.users',
        string='Assigned To',
        index=True,
    )
    job_start_date = fields.Date(string='Job Start Date')
    job_end_date = fields.Date(string='Job End Date')
    state_log_ids = fields.One2many(
        'ac.customer.job.state.log',
        'job_id',
        string='Activity Logs',
    )
    is_frozen = fields.Boolean(
        string='Frozen',
        compute='_compute_is_frozen',
        store=True,
    )
    line_ids = fields.One2many(
        'ac.customer.job.line',
        'job_id',
        string='Services',
        copy=True,
    )
    amount_untaxed = fields.Monetary(
        string='Subtotal',
        compute='_compute_amount_total',
        store=True,
        currency_field='currency_id',
    )
    amount_total = fields.Monetary(
        string='Grand Total',
        compute='_compute_amount_total',
        store=True,
        currency_field='currency_id',
    )
    payment_ids = fields.One2many(
        'ac.customer.job.payment',
        'job_id',
        string='Payments',
    )
    refund_ids = fields.One2many(
        'ac.customer.job.refund',
        'job_id',
        string='Refunds',
    )
    amount_paid = fields.Monetary(
        string='Paid Amount',
        compute='_compute_payment_amounts',
        store=True,
        currency_field='currency_id',
    )
    amount_remaining = fields.Monetary(
        string='Remaining Amount',
        compute='_compute_payment_amounts',
        store=True,
        currency_field='currency_id',
    )
    amount_refunded = fields.Monetary(
        string='Refunded Amount',
        compute='_compute_payment_amounts',
        store=True,
        currency_field='currency_id',
    )
    amount_refundable = fields.Monetary(
        string='Refundable Amount',
        compute='_compute_payment_amounts',
        store=True,
        currency_field='currency_id',
    )
    payment_percent = fields.Integer(
        string='Payment %',
        compute='_compute_payment_amounts',
        store=True,
    )
    payment_status = fields.Selection(
        selection=[
            ('unpaid', 'Unpaid'),
            ('partial', 'Partially Paid'),
            ('paid', 'Paid'),
        ],
        string='Payment Status',
        compute='_compute_payment_amounts',
        store=True,
    )
    customer_name = fields.Char(string='Name', compute='_compute_customer_fields', inverse='_inverse_customer_fields')
    customer_company = fields.Char(
        string='Customer Company',
        compute='_compute_customer_fields',
        inverse='_inverse_customer_fields',
    )
    customer_photo = fields.Image(string='Photo', compute='_compute_customer_fields', inverse='_inverse_customer_fields')
    customer_contact_number = fields.Char(
        string='Contact Number',
        compute='_compute_customer_fields',
        inverse='_inverse_customer_fields',
    )
    customer_email = fields.Char(string='Email', compute='_compute_customer_fields', inverse='_inverse_customer_fields')
    customer_aadhar_no = fields.Char(
        string='Aadhar Card No',
        compute='_compute_customer_fields',
        inverse='_inverse_customer_fields',
    )
    customer_pan_no = fields.Char(
        string='PAN Card No',
        compute='_compute_customer_fields',
        inverse='_inverse_customer_fields',
    )
    customer_house_no = fields.Char(
        string='House No/Flat No',
        compute='_compute_customer_fields',
        inverse='_inverse_customer_fields',
    )
    customer_street = fields.Char(
        string='Street Name',
        compute='_compute_customer_fields',
        inverse='_inverse_customer_fields',
    )
    customer_street2 = fields.Char(
        string='Street 2',
        compute='_compute_customer_fields',
        inverse='_inverse_customer_fields',
    )
    customer_city = fields.Char(string='City', compute='_compute_customer_fields', inverse='_inverse_customer_fields')
    customer_state_id = fields.Many2one(
        'res.country.state',
        string='State',
        compute='_compute_customer_fields',
        inverse='_inverse_customer_fields',
    )
    customer_country_id = fields.Many2one(
        'res.country',
        string='Country',
        compute='_compute_customer_fields',
        inverse='_inverse_customer_fields',
    )
    customer_zip = fields.Char(string='ZIP', compute='_compute_customer_fields', inverse='_inverse_customer_fields')
    customer_bank_account_number = fields.Char(
        string='Account Number',
        compute='_compute_customer_fields',
        inverse='_inverse_customer_fields',
    )
    customer_bank_ifsc_code = fields.Char(
        string='IFSC Code',
        compute='_compute_customer_fields',
        inverse='_inverse_customer_fields',
    )
    state_progress = fields.Integer(
        string='Progress',
        compute='_compute_state_progress',
        store=True,
    )

    @api.depends('state')
    def _compute_is_frozen(self):
        for job in self:
            job.is_frozen = job.state in FROZEN_STATES

    @api.depends('state')
    def _compute_state_progress(self):
        progress_map = {
            'not_started': 0,
            'started': 25,
            'in_progress': 50,
            'done': 100,
            'declined': 0,
        }
        for job in self:
            job.state_progress = progress_map.get(job.state, 0)

    @api.depends(
        'customer_id',
        'customer_id.name',
        'customer_id.customer_company',
        'customer_id.photo',
        'customer_id.contact_number',
        'customer_id.email',
        'customer_id.aadhar_no',
        'customer_id.pan_no',
        'customer_id.house_no',
        'customer_id.street',
        'customer_id.street2',
        'customer_id.city',
        'customer_id.state_id',
        'customer_id.country_id',
        'customer_id.zip',
        'customer_id.bank_account_number',
        'customer_id.bank_ifsc_code',
    )
    def _compute_customer_fields(self):
        for job in self:
            customer = job.customer_id
            if customer:
                for job_field, customer_field in CUSTOMER_FIELD_MAP.items():
                    job[job_field] = customer[customer_field]
            else:
                for job_field in CUSTOMER_FIELD_MAP:
                    job[job_field] = False

    def _format_display_value(self, field_name, value):
        if value in (False, None, ''):
            return ''
        field = self._fields.get(field_name)
        if not field:
            return str(value)
        if field.type == 'many2one':
            if isinstance(value, int):
                return self.env[field.comodel_name].browse(value).display_name
            return value.display_name if value else ''
        if field.type == 'selection':
            return dict(field.selection).get(value, value)
        if field.type == 'boolean':
            return _('Yes') if value else _('No')
        if field.type == 'monetary':
            return '{:.2f}'.format(value)
        return str(value)

    def _values_differ(self, field_name, old_value, new_value):
        field = self._fields[field_name]
        if field.type == 'many2one':
            old_id = old_value.id if old_value else False
            new_id = new_value if isinstance(new_value, int) else getattr(new_value, 'id', new_value)
            return old_id != new_id
        return old_value != new_value

    def _log_activity(self, log_type, field_label=None, old_value=None, new_value=None,
                      from_state=None, to_state=None, payment_id=None, has_upi_screenshot=False):
        self.ensure_one()
        vals = {
            'job_id': self.id,
            'user_id': self.env.user.id,
            'log_type': log_type,
            'field_name': field_label,
            'old_value': old_value,
            'new_value': new_value,
            'from_state': from_state,
            'to_state': to_state,
        }
        if payment_id:
            vals['payment_id'] = payment_id
            vals['has_upi_screenshot'] = bool(has_upi_screenshot)
        self.env['ac.customer.job.state.log'].sudo().create(vals)

    def _log_field_changes(self, vals):
        if self.env.context.get('skip_job_activity_log'):
            return
        for job in self:
            for field_name, label in JOB_TRACKED_FIELDS.items():
                if field_name not in vals or field_name == 'state':
                    continue
                old_value = job[field_name]
                new_value = vals[field_name]
                if job._values_differ(field_name, old_value, new_value):
                    job._log_activity(
                        'field_update',
                        field_label=label,
                        old_value=job._format_display_value(field_name, old_value),
                        new_value=job._format_display_value(field_name, new_value),
                    )

    def _check_not_frozen(self):
        frozen = self.filtered(lambda job: job.state in FROZEN_STATES)
        if frozen:
            raise UserError(_('Service engagements marked as Done or Declined cannot be modified.'))

    def _check_state_transition(self, new_state):
        """Block leaving/entering final states except via action buttons."""
        for job in self:
            if job.state in FROZEN_STATES and new_state != job.state:
                raise UserError(_(
                    'Service engagements marked as Done or Declined are final and cannot be moved to another state.'
                ))
            if (
                new_state in FROZEN_STATES
                and job.state != new_state
                and not self.env.context.get('ac_allow_state_change')
            ):
                raise UserError(_(
                    'Please use the Mark Done or Mark Declined button to set this final state.'
                ))

    def write(self, vals):
        if 'state' in vals:
            self._check_state_transition(vals['state'])
        # Allow trusted state transitions into Done/Declined from action buttons.
        allowed_state_write_fields = {'state', 'job_start_date', 'job_end_date'}
        if self.env.context.get('ac_allow_state_change') and set(vals.keys()) <= allowed_state_write_fields:
            res = super().write(vals)
            self._sync_receivable_statement()
            return res
        self._check_not_frozen()
        self._log_field_changes(vals)
        res = super().write(vals)
        if any(field in vals for field in ('customer_id', 'company_id', 'state', 'amount_total')):
            self._sync_receivable_statement()
        return res

    def unlink(self):
        self._check_not_frozen()
        statements = self.env['ac.customer.statement.line'].sudo().search([
            ('job_id', 'in', self.ids),
            ('transaction_type', '=', 'receivable'),
            ('state', '=', 'posted'),
        ])
        statements.write({'state': 'cancelled'})
        return super().unlink()

    def _sync_receivable_statement(self):
        """Post receivable debit only after the engagement has started.

        not_started is treated as draft — no statement line is recorded yet.
        """
        Statement = self.env['ac.customer.statement.line'].sudo()
        draft_or_closed = ('not_started', 'declined')
        for job in self:
            if not job.customer_id:
                continue
            existing = Statement.search([
                ('job_id', '=', job.id),
                ('transaction_type', '=', 'receivable'),
                ('state', '=', 'posted'),
            ], limit=1)
            rounding = job.currency_id.rounding if job.currency_id else 0.01
            if (
                job.state in draft_or_closed
                or float_is_zero(job.amount_total, precision_rounding=rounding)
            ):
                if existing:
                    existing.write({'state': 'cancelled'})
                continue

            date = job.job_start_date or (
                fields.Date.to_date(job.create_date) if job.create_date else fields.Date.context_today(job)
            )
            vals = {
                'name': _('Service Receivable: %s') % job.name,
                'date': date,
                'customer_id': job.customer_id.id,
                'company_id': job.company_id.id,
                'transaction_type': 'receivable',
                'debit': job.amount_total,
                'credit': 0.0,
                'job_id': job.id,
                'state': 'posted',
            }
            if existing:
                existing.write(vals)
            else:
                Statement.create(vals)

    def _inverse_customer_fields(self):
        for job in self:
            if job.state in FROZEN_STATES:
                continue
            if not job.customer_id:
                continue
            changes = []
            vals = {}
            for job_field, customer_field in CUSTOMER_FIELD_MAP.items():
                new_value = job[job_field]
                old_value = job.customer_id[customer_field]
                if old_value != new_value:
                    changes.append((job_field, old_value, new_value))
                    vals[customer_field] = new_value
            if vals:
                job.customer_id.write(vals)
            for job_field, old_value, new_value in changes:
                job._log_activity(
                    'field_update',
                    field_label=job._fields[job_field].string,
                    old_value=job._format_display_value(job_field, old_value),
                    new_value=job._format_display_value(job_field, new_value),
                )

    @api.onchange('customer_id')
    def _onchange_customer_id(self):
        customer = self.customer_id
        if customer:
            for job_field, customer_field in CUSTOMER_FIELD_MAP.items():
                self[job_field] = customer[customer_field]
            if customer.company_id:
                self.company_id = customer.company_id
        else:
            for job_field in CUSTOMER_FIELD_MAP:
                self[job_field] = False

    @api.onchange('customer_country_id')
    def _onchange_customer_country_id(self):
        if self.customer_state_id and self.customer_state_id.country_id != self.customer_country_id:
            self.customer_state_id = False

    @api.depends('line_ids.amount')
    def _compute_amount_total(self):
        for job in self:
            subtotal = sum(job.line_ids.mapped('amount'))
            job.amount_untaxed = subtotal
            job.amount_total = subtotal

    @api.depends(
        'payment_ids.amount',
        'payment_ids.state',
        'refund_ids.amount',
        'refund_ids.state',
        'amount_total',
    )
    def _compute_payment_amounts(self):
        for job in self:
            posted_payments = job.payment_ids.filtered(lambda payment: payment.state == 'posted')
            approved_refunds = job.refund_ids.filtered(lambda refund: refund.state == 'approved')
            job.amount_paid = sum(posted_payments.mapped('amount'))
            job.amount_refunded = sum(approved_refunds.mapped('amount'))
            job.amount_refundable = job.amount_paid - job.amount_refunded
            job.amount_remaining = job.amount_total - job.amount_paid

            rounding = job.currency_id.rounding if job.currency_id else 0.01
            if float_is_zero(job.amount_total, precision_rounding=rounding):
                job.payment_percent = 0
                job.payment_status = 'unpaid'
                continue

            percent = int(round((job.amount_paid / job.amount_total) * 100))
            job.payment_percent = max(0, min(100, percent))

            if float_compare(job.amount_paid, 0.0, precision_rounding=rounding) <= 0:
                job.payment_status = 'unpaid'
            elif float_compare(job.amount_paid, job.amount_total, precision_rounding=rounding) >= 0:
                job.payment_status = 'paid'
                job.payment_percent = 100
            else:
                job.payment_status = 'partial'

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('ac.customer.job') or 'New'
        if vals.get('customer_id') and not vals.get('company_id'):
            customer = self.env['ac.customer.master'].browse(vals['customer_id'])
            if customer.company_id:
                vals['company_id'] = customer.company_id.id
        job = super().create(vals)
        job._sync_receivable_statement()
        return job

    def action_record_payment(self):
        self.ensure_one()
        if self.state == 'declined':
            raise UserError(_('Payments cannot be recorded on declined engagements.'))
        if self.amount_remaining <= 0:
            raise UserError(_('This engagement has no remaining balance to pay.'))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Record Payment'),
            'res_model': 'ac.customer.job.payment.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_job_id': self.id,
                'default_payment_scope': 'full',
                'default_amount': self.amount_remaining,
            },
        }

    def action_request_refund(self):
        self.ensure_one()
        if self.state != 'declined':
            raise UserError(_('Refunds can only be requested on declined engagements.'))
        if self.amount_refundable <= 0:
            raise UserError(_('There is no refundable payment balance on this engagement.'))
        pending = self.refund_ids.filtered(lambda refund: refund.state == 'waiting_approval')
        if pending:
            raise UserError(_(
                'There is already a refund waiting for approval (%s).'
            ) % pending[0].name)
        return {
            'type': 'ir.actions.act_window',
            'name': _('Request Refund'),
            'res_model': 'ac.customer.job.refund.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_job_id': self.id,
                'default_refund_scope': 'full',
                'default_amount': self.amount_refundable,
            },
        }

    def action_assign_to(self):
        self.ensure_one()
        self._check_not_frozen()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Assign To',
            'res_model': 'ac.customer.job.assign.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_job_id': self.id},
        }

    def _log_state_change(self, from_state, to_state):
        self._log_activity(
            'state_change',
            from_state=from_state,
            to_state=to_state,
        )

    def _notify_success(self, message):
        """Refresh the form in place and show a success effect (no full page reload)."""
        return {
            'type': 'ir.actions.act_window_close',
            'effect': {
                'fadeout': 'slow',
                'message': message,
                'type': 'rainbow_man',
            },
        }

    def _change_state(self, expected_state, new_state, extra_vals=None):
        extra_vals = extra_vals or {}
        for job in self:
            if job.state != expected_state:
                state_label = dict(self._fields['state'].selection).get(expected_state, expected_state)
                raise UserError(
                    _('This action is only available when the engagement is in the "%s" state.') % state_label
                )
            from_state = job.state
            vals = {'state': new_state, **extra_vals}
            job.with_context(ac_allow_state_change=True).write(vals)
            job._log_state_change(from_state, new_state)

    def action_mark_started(self):
        self._change_state('not_started', 'started', {
            'job_start_date': fields.Date.context_today(self),
        })
        return self._notify_success(_('The service engagement has been marked as Started.'))

    def action_mark_in_progress(self):
        self._change_state('started', 'in_progress')
        return self._notify_success(_('The service engagement has been marked as In Progress.'))

    def action_mark_done(self):
        self._change_state('in_progress', 'done', {
            'job_end_date': fields.Date.context_today(self),
        })
        return self._notify_success(_('The service engagement has been marked as Done.'))

    def action_mark_declined(self):
        for job in self:
            if job.state in FROZEN_STATES:
                raise UserError(_('This engagement cannot be marked as declined.'))
            from_state = job.state
            job.with_context(ac_allow_state_change=True).write({'state': 'declined'})
            job._log_state_change(from_state, 'declined')
        return self._notify_success(_('The service engagement has been marked as Declined.'))
