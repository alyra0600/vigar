from odoo import models, _
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

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
