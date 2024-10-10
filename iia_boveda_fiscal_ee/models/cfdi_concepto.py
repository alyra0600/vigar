from odoo import api, fields, models

class CfdiConceptos(models.Model):
    _name = 'iia_boveda_fiscal.cfdi.concepto'
    _description = 'CFDI concepto'
    _check_company_auto = True
    _rec_name = "descripcion"

    def _get_last_sequence(self):
        val = self.search([], order='sequence DESC', limit=1)
        if len(val) > 0:
            sequence = val.sequence + 1
        else:
            sequence = 1
        return sequence

    sequence = fields.Integer(string='Secuencia', required=True, default=_get_last_sequence)
    company_id = fields.Many2one(comodel_name='res.company', string='Empresa', related='iia_boveda_fiscal_cfdi_id.company_id', readonly=True)
    code_cfdi = fields.Char(string='UUID', readonly=True)
    fecha = fields.Date(string='Fecha', readonly=True)
    folio = fields.Char(string='Folio', readonly=True)
    forma_pago = fields.Char(string='Forma de pago', readonly=True)
    lugar_expedicion = fields.Char(string='Lugar de expedición',readonly=True)
    metodo_pago = fields.Selection(selection=[('PPD', 'PPD'), ('PUE', 'PUE'),], string='Método de pago', readonly=True)
    moneda = fields.Char(string='Moneda', readonly=True)
    no_certificado = fields.Char(string='Nro. de certificado', readonly=True)
    sello = fields.Char(string='Sello', readonly=True)
    serie = fields.Char(string='Serie', readonly=True)
    subtotal = fields.Float(string='Subtotal', readonly=True)
    tipo_de_comprobante = fields.Selection(selection=[
        ('I', u'Facturas de clientes'),
        ('SI', u'Facturas de proveedor'),
        ('E', u'Notas de crédito cliente'),
        ('SE', u'Notas de crédito proveedor'),
        ('P', u'REP de clientes'),
        ('SP', u'REP de proveedores'),
        ('N', u'Nóminas de empleados'),
        ('SN', u'Nómina propia'),
        ('T', u'Factura de traslado cliente'),
        ('ST', u'Factura de traslado proveedor'),
    ], string='Tipo de comprobante', index=True, readonly=True, default='SI')
    total = fields.Float(string='Total', readonly=True)
    version = fields.Char(string='Versión', readonly=True)
    partner_id_emisor = fields.Many2one(comodel_name='res.partner', string='Emisor', readonly=True)
    partner_id_receptor = fields.Many2one(comodel_name='res.partner', string='Receptor', readonly=True)
    cantidad = fields.Float(string='Cantidad', digits='Product Unit of Measure', readonly=True)
    clave_prod_serv = fields.Char(string='Clave', readonly=True)
    clave_unidad = fields.Char(string='Clave unidad', readonly=True)
    descripcion = fields.Char(string='Descripción', readonly=True)
    descuento = fields.Float(string='Descuento',readonly=True, default=0)
    importe = fields.Float(string='Importe', readonly=True, default=0)
    valor_unitario = fields.Float(string='Valor unitario', digits='Product Price', readonly=True, default=0)
    no_identificacion = fields.Char(string='Identificación', readonly=True)
    unidad = fields.Char(string='Unidad', readonly=True)
    uom_id = fields.Many2one(comodel_name='uom.uom', string='Unidad de medida')
    unspsc_product_category_id = fields.Many2one(comodel_name='product.unspsc.code', string='Categoria')
    product_tmpl_id = fields.Many2one(comodel_name='product.template', string='Plantilla del producto')
    product_id = fields.Many2one(comodel_name='product.product', string='Producto')
    account_id = fields.Many2one(comodel_name='account.account', string='Cuenta contable')
    account_analytic_account_id = fields.Many2one(comodel_name='account.analytic.account', string='Cuenta anaítica',)
    analytic_distribution = fields.Json(string="Distribución analítica")
    analytic_precision = fields.Integer(string="Precisión analítica", store=False, default=lambda self: self.env['decimal.precision'].precision_get("Percentage Analytic"))
    tax_ids = fields.One2many('iia_boveda_fiscal.cfdi.concepto.tax', 'iia_boveda_fiscal_cfdi_concepto_id', string='Impuestos')
    iia_boveda_fiscal_cfdi_id = fields.Many2one(comodel_name='iia_boveda_fiscal.cfdi', string='CFDI', required=True, ondelete="cascade")

    @api.onchange('product_tmpl_id')
    def onchange_product_tmpl_id(self):
        if self.tipo_de_comprobante in ['SI', 'SE'] and not self.account_id:
            if self.product_tmpl_id.property_account_expense_id:
                self.account_id = self.product_tmpl_id.property_account_expense_id
            elif self.product_tmpl_id.categ_id.property_account_expense_categ_id:
                self.account_id = self.product_tmpl_id.categ_id.property_account_expense_categ_id
        elif self.tipo_de_comprobante in ['I', 'E'] and not self.account_id:
            if self.product_tmpl_id.property_account_income_id:
                self.account_id = self.product_tmpl_id.property_account_income_id
            elif self.product_tmpl_id.categ_id.property_account_income_categ_id:
                self.account_id = self.product_tmpl_id.categ_id.property_account_income_categ_id
        if not self.product_id:
            self.product_id = self.env['product.product'].search([('product_tmpl_id', '=', self.product_tmpl_id.id)], limit=1)