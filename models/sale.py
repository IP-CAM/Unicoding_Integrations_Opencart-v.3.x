from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    opencartid = fields.Char('OpenCart ID')
    unicoding_integrations_id = fields.Many2one(
        string='Unicoding integration ID',
        comodel_name='unicoding.integrations',
        ondelete='restrict',
        copy=False,
    )
