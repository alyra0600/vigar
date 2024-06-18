# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from datetime import datetime

class CreatePurchaseOrderCfdi(models.TransientModel):
    _name = 'create.purchaseorder.cfdi'
    _description = "Orden de compra desde CFDI"

    new_order_line_ids = fields.One2many('getcfdi.data', 'new_order_line_id', string="Lineas")
    partner_id = fields.Many2one('res.partner', string='Proveedor', required=True)
    date_order = fields.Datetime(string='Fecha Orden', required=True, copy=False)

    @api.model
    def default_get(self, default_fields):
        res = super(CreatePurchaseOrderCfdi, self).default_get(default_fields)
        data = self.env['iia_boveda_fiscal.cfdi'].browse(self._context.get('active_ids', []))
        update = []
        for record in data.concepto_ids:
            product = self.env['product.product'].search([('product_tmpl_id', '=', record.product_tmpl_id.id)], limit=1)
            update.append((0, 0, {
                'product_id': product.id,
                'product_uom': record.product_tmpl_id.uom_po_id.id,
                'name': record.descripcion,
                'product_qty': record.cantidad,
                'price_unit': record.valor_unitario,
                'product_subtotal': record.importe,
            }))
        res.update({'new_order_line_ids': update,
                    'partner_id': data.partner_id_emisor.id,
                    'date_order': data.fecha})
        return res

    def action_create_purchase_order(self):
        self.ensure_one()
        res = self.env['purchase.order'].browse(self._context.get('id', []))
        cfdi = self.env['iia_boveda_fiscal.cfdi'].browse(self._context.get('active_id'))
        cfdi_name = cfdi.id
        company_id = self.env.company

        if self.partner_id.property_purchase_currency_id:
            currency_id = self.partner_id.property_purchase_currency_id.id
        else:
            currency_id = self.env.company.currency_id.id

        purchase_order = res.create({
            'partner_id': self.partner_id.id,
            'date_order': str(self.date_order),
            'cfdi_origin_id': cfdi_name,
            'partner_ref': cfdi.partner_id_emisor.name,
            'currency_id': currency_id
        })
        for data in self.new_order_line_ids:
            product_quantity = data.product_qty
            purchase_qty_uom = data.product_uom._compute_quantity(product_quantity, data.product_id.uom_po_id)

            supplierinfo = data.product_id._select_seller(
                partner_id=purchase_order.partner_id,
                quantity=purchase_qty_uom,
                date=purchase_order.date_order and purchase_order.date_order.date(),
                uom_id=data.product_id.uom_po_id
            )
            fpos = purchase_order.fiscal_position_id
            taxes = fpos.map_tax(data.product_id.supplier_taxes_id)
            if taxes:
                taxes = taxes.filtered(lambda t: t.company_id.id == company_id.id)
            if not supplierinfo:
                po_line_uom = data.product_uom or data.product_id.uom_po_id
                price_unit = self.env['account.tax']._fix_tax_included_price_company(
                    data.product_id.uom_id._compute_price(data.product_id.standard_price, po_line_uom),
                    data.product_id.supplier_taxes_id,
                    taxes,
                    company_id,
                )
                if price_unit and data.order_id.currency_id and data.order_id.company_id.currency_id != data.order_id.currency_id:
                    price_unit = data.order_id.company_id.currency_id._convert(
                        price_unit,
                        data.order_id.currency_id,
                        data.order_id.company_id,
                        self.date_order or fields.Date.today(),
                    )

            # compute unit price
            if supplierinfo:
                price_unit = self.env['account.tax'].sudo()._fix_tax_included_price_company(supplierinfo.price,
                                                                                            data.product_id.supplier_taxes_id,
                                                                                            taxes, company_id)
                if purchase_order.currency_id and supplierinfo.currency_id != purchase_order.currency_id:
                    price_unit = supplierinfo.currency_id._convert(price_unit, purchase_order.currency_id,
                                                                   purchase_order.company_id, fields.datetime.today()) 

            if self.partner_id.property_purchase_currency_id :
                value = {
                    'product_id': data.product_id.id,
                    'name': data.name,
                    'product_qty': data.product_qty,
                    'order_id': purchase_order.id,
                    'product_uom': data.product_uom.id,
                    'taxes_id': data.product_id.supplier_taxes_id.ids,
                    'date_planned': data.date_planned,
                    'price_unit': data.price_unit,
                }
            else:
                value = {
                    'product_id': data.product_id.id,
                    'name': data.name,
                    'product_qty': data.product_qty,
                    'order_id': purchase_order.id,
                    'product_uom': data.product_uom.id,
                    'taxes_id': data.product_id.supplier_taxes_id.ids,
                    'date_planned': data.date_planned,
                    'price_unit': data.price_unit,
                }
            self.env['purchase.order.line'].create(value)
        return purchase_order


class GetCfdiData(models.TransientModel):
    _name = 'getcfdi.data'
    _description = "Obtener información CFDI"

    new_order_line_id = fields.Many2one('create.purchaseorder.cfdi')

    product_id = fields.Many2one('product.product', string="Producto", required=True)
    name = fields.Char(string="Descripcion")
    product_qty = fields.Float(string='Cantidad', required=True)
    date_planned = fields.Datetime(string='Fecha Planeada', default=datetime.today())
    product_uom = fields.Many2one('uom.uom', string='Unidad de Medida')
    # order_id = fields.Many2one('sale.order', string='Order Reference', ondelete='cascade', index=True)
    price_unit = fields.Float(string='Precio Unitario', digits='Product Price')
    product_subtotal = fields.Float(string="SubTotal", compute='_compute_total')

    @api.depends('product_qty', 'price_unit')
    def _compute_total(self):
        for record in self:
            record.product_subtotal = record.product_qty * record.price_unit
