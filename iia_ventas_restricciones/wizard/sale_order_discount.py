from odoo import models, _
from odoo.exceptions import AccessError


class SaleOrderDiscount(models.TransientModel):
    _inherit = 'sale.order.discount'

    def action_apply_discount(self):
        if not self.env.user.has_group('iia_ventas_restricciones.group_can_apply_discount'):
            raise AccessError(_('No tiene permiso para aplicar descuentos.'))
        return super().action_apply_discount()
