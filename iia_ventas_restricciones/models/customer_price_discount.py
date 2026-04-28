from odoo import fields, models


class CustomerPriceDiscount(models.Model):
    _name = 'customer.price.discount'
    _description = 'Precio y Descuento por Cliente'
    _rec_name = 'product_id'
    _order = 'partner_id, product_id'

    partner_id = fields.Many2one('res.partner', string='Cliente', required=True, ondelete='cascade', index=True)
    product_id = fields.Many2one('product.product', string='Producto', required=True, ondelete='cascade', index=True)
    price_unit = fields.Float(string='Precio Unitario', digits='Product Price')
    discount = fields.Float(string='Descuento (%)', digits='Discount')

    _sql_constraints = [
        ('partner_product_unique', 'UNIQUE(partner_id, product_id)',
         'Ya existe un precio/descuento para este cliente y producto.'),
    ]
