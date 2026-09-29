from odoo import _, api, fields, models
from odoo.exceptions import UserError

FROZEN_STATES = ('done', 'declined')

LINE_TRACKED_FIELDS = {
    'service_id': 'Service',
    'description': 'Description',
    'amount': 'Amount',
}


class AcCustomerJobLine(models.Model):
    _name = 'ac.customer.job.line'
    _description = 'Service Engagement Line'
    _order = 'sequence, id'

    job_id = fields.Many2one(
        'ac.customer.job',
        string='Service Engagement',
        required=True,
        ondelete='cascade',
        index=True,
    )
    sequence = fields.Integer(default=10)
    slno = fields.Integer(
        string='Sl No',
        compute='_compute_slno',
        store=True,
    )
    company_id = fields.Many2one(related='job_id.company_id', store=True)
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        related='job_id.currency_id',
        store=True,
        readonly=True,
    )
    service_id = fields.Many2one(
        'ac.service',
        string='Service',
        required=True,
        ondelete='restrict',
    )
    description = fields.Text(string='Description')
    amount = fields.Monetary(
        string='Amount',
        required=True,
        currency_field='currency_id',
        default=0.0,
    )

    @api.depends('job_id', 'job_id.line_ids', 'sequence')
    def _compute_slno(self):
        for job in self.mapped('job_id'):
            for index, line in enumerate(job.line_ids, start=1):
                line.slno = index
        for line in self:
            if not line.job_id:
                line.slno = 1

    def _service_summary(self):
        self.ensure_one()
        return '%s - %s' % (self.service_id.display_name, self.amount)

    def _format_line_display_value(self, field_name, value):
        if value in (False, None, ''):
            return ''
        field = self._fields.get(field_name)
        if not field:
            return str(value)
        if field.type == 'many2one':
            return value.display_name if value else ''
        if field.type == 'monetary':
            return '{:.2f}'.format(value)
        return str(value)

    def _log_service_activity(self, log_type, field_label=None, old_value=None, new_value=None):
        self.ensure_one()
        self.job_id._log_activity(
            log_type,
            field_label=field_label,
            old_value=old_value,
            new_value=new_value,
        )

    def _check_job_not_frozen(self):
        frozen_jobs = self.mapped('job_id').filtered(lambda job: job.state in FROZEN_STATES)
        if frozen_jobs:
            raise UserError(_('Cannot modify services on engagements marked as Done or Declined.'))

    @api.model
    def create(self, vals):
        if vals.get('job_id'):
            job = self.env['ac.customer.job'].browse(vals['job_id'])
            if job.state in FROZEN_STATES:
                raise UserError(_('Cannot add services to engagements marked as Done or Declined.'))
        lines = super().create(vals)
        if not self.env.context.get('skip_job_activity_log'):
            for line in lines:
                line._log_service_activity(
                    'service_add',
                    field_label=_('Service'),
                    new_value=line._service_summary(),
                )
        lines.mapped('job_id')._sync_receivable_statement()
        return lines

    def write(self, vals):
        self._check_job_not_frozen()
        tracked_vals = {key: value for key, value in vals.items() if key in LINE_TRACKED_FIELDS}
        old_values = {}
        if tracked_vals:
            for line in self:
                old_values[line.id] = {field: line[field] for field in tracked_vals}
        result = super().write(vals)
        if tracked_vals and not self.env.context.get('skip_job_activity_log'):
            for line in self:
                for field_name, label in LINE_TRACKED_FIELDS.items():
                    if field_name not in tracked_vals:
                        continue
                    old_value = old_values[line.id][field_name]
                    new_value = line[field_name]
                    if old_value != new_value:
                        line._log_service_activity(
                            'service_update',
                            field_label=label,
                            old_value=line._format_line_display_value(field_name, old_value),
                            new_value=line._format_line_display_value(field_name, new_value),
                        )
        if 'amount' in vals:
            self.mapped('job_id')._sync_receivable_statement()
        return result

    def unlink(self):
        self._check_job_not_frozen()
        jobs = self.mapped('job_id')
        if not self.env.context.get('skip_job_activity_log'):
            for line in self:
                line._log_service_activity(
                    'service_remove',
                    field_label=_('Service'),
                    old_value=line._service_summary(),
                )
        result = super().unlink()
        jobs._sync_receivable_statement()
        return result
    @api.onchange('service_id')
    def _onchange_service_id(self):
        if not self.service_id:
            self.description = False
            self.amount = 0.0
            return
        service = self.service_id
        self.description = service.description or service.name
        company = self.company_id or self.env.company
        company_currency = self.currency_id or company.currency_id
        amount = service.amount or 0.0
        if service.currency_id and company_currency and service.currency_id != company_currency:
            amount = service.currency_id._convert(
                amount,
                company_currency,
                company,
                fields.Date.context_today(self),
            )
        self.amount = amount
