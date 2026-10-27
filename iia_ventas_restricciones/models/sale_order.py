from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    iia_puede_cambiar_precio = fields.Boolean(string='Puede modificar precios', compute='_compute_iia_permisos_linea')
    iia_puede_aplicar_descuento = fields.Boolean(string='Puede aplicar descuentos', compute='_compute_iia_permisos_linea')

    @api.depends_context('uid')
    def _compute_iia_permisos_linea(self):
        puede_cambiar_precio = self.env.user.has_group('iia_ventas_restricciones.group_can_change_price')
        puede_aplicar_descuento = self.env.user.has_group('iia_ventas_restricciones.group_can_apply_discount')
        for order in self:
            order.iia_puede_cambiar_precio = puede_cambiar_precio
            order.iia_puede_aplicar_descuento = puede_aplicar_descuento

    def _action_cancel(self):
        self.invoice_ids.filtered(lambda inv: inv.state == 'draft').with_context(from_cancel_wizard=True).button_cancel()
        return super()._action_cancel()

    def _recompute_prices(self):
        return super(SaleOrder, self.sudo())._recompute_prices()

    def action_open_discount_wizard(self):
        if not self.env.user.has_group('iia_ventas_restricciones.group_can_apply_discount'):
            raise AccessError(_('No tiene permiso para aplicar descuentos.'))
        return super().action_open_discount_wizard()

    def action_save_customer_prices(self):
        self.ensure_one()
        if not self.partner_id:
            raise UserError(_('El pedido debe tener un cliente asignado.'))
        CustomerPrice = self.env['customer.price.discount']
        for line in self.order_line.filtered(lambda l: l.product_id):
            existing = CustomerPrice.search([
                ('partner_id', '=', self.partner_id.id),
                ('product_id', '=', line.product_id.id),
            ], limit=1)
            vals = {'price_unit': line.price_unit, 'discount': line.discount}
            if existing:
                existing.write(vals)
            else:
                CustomerPrice.create({
                    'partner_id': self.partner_id.id,
                    'product_id': line.product_id.id,
                    **vals,
                })
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Precios guardados'),
                'message': _('Precios y descuentos guardados para %s.') % self.partner_id.name,
                'type': 'success',
                'sticky': False,
            },
        }
