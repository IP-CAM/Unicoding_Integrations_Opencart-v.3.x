from odoo import api, fields, models


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    opencartid = fields.Char('OpenCart ID')
    unicoding_integrations_id = fields.Many2one(
        string='Unicoding integration ID',
        comodel_name='unicoding.integrations',
        ondelete='restrict',
        copy=False,
    )