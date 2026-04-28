from odoo import models, api, _
from odoo.exceptions import AccessError


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    def _compute_price_unit(self):
        super()._compute_price_unit()
        for line in self:
            if not line.product_id or not line.order_id.partner_id:
                continue
            record = self.env['customer.price.discount'].search([
                ('partner_id', '=', line.order_id.partner_id.id),
                ('product_id', '=', line.product_id.id),
            ], limit=1)
            if record and record.price_unit > 0:
                line.price_unit = record.price_unit

    def _compute_discount(self):
        super()._compute_discount()
        for line in self:
            if not line.product_id or not line.order_id.partner_id:
                continue
            record = self.env['customer.price.discount'].search([
                ('partner_id', '=', line.order_id.partner_id.id),
                ('product_id', '=', line.product_id.id),
            ], limit=1)
            if record and record.discount > 0:
                line.discount = record.discount

    def write(self, vals):
        if 'price_unit' in vals:
            if not self.env.user.has_group('iia_ventas_restricciones.group_can_change_price'):
                raise AccessError(_('No tiene permiso para modificar precios.'))
        if 'discount' in vals:
            if not self.env.user.has_group('iia_ventas_restricciones.group_can_apply_discount'):
                raise AccessError(_('No tiene permiso para aplicar descuentos.'))
        return super().write(vals)
