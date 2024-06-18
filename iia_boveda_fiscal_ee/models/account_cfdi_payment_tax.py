from odoo import api, fields, models

class AccountCfdiPaymentTax(models.Model):
    _name = 'account.cfdi.payment.tax'
    _description = 'Relación de impuestos en CFDI pagados'

    name = fields.Char(string="Documento relacionado")
    folio = fields.Char(string="Folio")
    serie = fields.Char(string="Serie")
    currency = fields.Char(string="Moneda")
    subject_tax = fields.Char(string="Objeto de impuesto")
    type_tax = fields.Selection(string="Tipo de impuesto", selection=[('001','ISR'),('002','IVA'),('003','IEPS')])
    base_tax = fields.Char(string="Base")
    base_amount = fields.Float(string="Importe base")
    tax_amount = fields.Float(string="Importe impuesto")
    paid_amount = fields.Float(string="Importe pagado")
    previous_balance = fields.Float(string="Saldo anterior")
    current_balance = fields.Float(string="Saldo actual")
    currency_rate = fields.Float(string="Tasa de cambio")
    cfdi_id = fields.Many2one(comodel_name="iia_boveda_fiscal.cfdi", string="CFDI")
    exempt_tax = fields.Boolean(string="Impuesto excento")
    cfdi_type = fields.Selection(string="Tipo de comprobante", related="cfdi_id.tipo_de_comprobante", store=True)
    payment_date = fields.Date(string="Fecha de pago")
    cfdi_date = fields.Date(string="Fecha de timbrado", related="cfdi_id.fecha", store=True)
    company_id = fields.Many2one(comodel_name="res.company", related="cfdi_id.company_id", store=True)
    recipient_id = fields.Many2one(comodel_name="res.partner", string="Receptor", related="cfdi_id.partner_id_receptor", store=True)
    emitter_id = fields.Many2one(comodel_name="res.partner", string="Emisor", related="cfdi_id.partner_id_emisor", store=True)