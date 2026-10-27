from odoo import models, api, _
from odoo.exceptions import AccessError
from odoo.tools import float_compare


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

    def _iia_valor_cambia(self, field_name, value):
        digits = self._fields[field_name].get_digits(self.env)
        precision = digits[1] if digits else 2
        return any(float_compare(line[field_name], value or 0.0, precision_digits=precision) for line in self)

    def _iia_es_linea_especial(self):
        self.ensure_one()
        if self.display_type or self.is_downpayment or self.is_expense or self._is_discount_line():
            return True
        return any(self[campo] for campo in ('is_delivery', 'is_reward_line') if campo in self._fields)

    def _iia_validar_candados(self, vals):
        if 'price_unit' in vals and self._iia_valor_cambia('price_unit', vals['price_unit']):
            if not self.env.user.has_group('iia_ventas_restricciones.group_can_change_price'):
                raise AccessError(_('No tiene permiso para modificar precios.'))
        if 'discount' in vals and self._iia_valor_cambia('discount', vals['discount']):
            if not self.env.user.has_group('iia_ventas_restricciones.group_can_apply_discount'):
                raise AccessError(_('No tiene permiso para aplicar descuentos.'))

    @api.model_create_multi
    def create(self, vals_list):
        if not self.env.su:
            for vals in vals_list:
                if not vals.get('product_id') or ('price_unit' not in vals and 'discount' not in vals):
                    continue
                linea = self.new({campo: valor for campo, valor in vals.items() if campo not in ('price_unit', 'discount')})
                if not linea._iia_es_linea_especial():
                    linea._iia_validar_candados(vals)
        return super().create(vals_list)

    def write(self, vals):
        if not self.env.su:
            self.filtered(lambda line: not line._iia_es_linea_especial())._iia_validar_candados(vals)
        return super().write(vals)
