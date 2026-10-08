from odoo import models, api, _
from odoo.exceptions import AccessError
from odoo.tools import float_compare


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

    def _iia_valor_cambia(self, field_name, value):
        digits = self._fields[field_name].get_digits(self.env)
        precision = digits[1] if digits else 2
        return any(float_compare(line[field_name], value or 0.0, precision_digits=precision) for line in self)

    def write(self, vals):
        if 'price_unit' in vals and self._iia_valor_cambia('price_unit', vals['price_unit']):
            if not self.env.user.has_group('iia_ventas_restricciones.group_can_change_price'):
                raise AccessError(_('No tiene permiso para modificar precios en facturas.'))
        if 'discount' in vals and self._iia_valor_cambia('discount', vals['discount']):
            if not self.env.user.has_group('iia_ventas_restricciones.group_can_apply_discount'):
                raise AccessError(_('No tiene permiso para aplicar descuentos en facturas.'))
        return super().write(vals)
