from odoo import models, api, _
from odoo.exceptions import AccessError


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    @api.onchange('product_id')
    def _onchange_product_id_customer_price(self):
        if not self.product_id or not self.move_id.partner_id:
            return
        record = self.env['customer.price.discount'].search([
            ('partner_id', '=', self.move_id.partner_id.id),
            ('product_id', '=', self.product_id.id),
        ], limit=1)
        if record:
            if record.price_unit > 0:
                self.price_unit = record.price_unit
            if record.discount > 0:
                self.discount = record.discount

    def write(self, vals):
        if 'price_unit' in vals:
            if not self.env.user.has_group('iia_ventas_restricciones.group_can_change_price'):
                raise AccessError(_('No tiene permiso para modificar precios en facturas.'))
        if 'discount' in vals:
            if not self.env.user.has_group('iia_ventas_restricciones.group_can_apply_discount'):
                raise AccessError(_('No tiene permiso para aplicar descuentos en facturas.'))
        return super().write(vals)
