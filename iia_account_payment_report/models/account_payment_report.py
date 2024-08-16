from odoo import api, fields, models

class AccountPaymentReport(models.TransientModel):
    _name = 'account.payment.report'
    _description = 'Reporte de pagos'
    _rec_name = "invoice_id"

    invoice_id = fields.Many2one(comodel_name="account.move", string="Factura")
    payment_id = fields.Many2one(comodel_name="account.move", string="Pago")
    invoice_date = fields.Date(string="Fecha de factura")
    payment_date = fields.Date(string="Fecha de pago")
    journal_id = fields.Many2one(comodel_name="account.journal", string="Diario")
    amount_total = fields.Float(string="Importe")
    currency_id = fields.Many2one(comodel_name="res.currency", string="Divisa")
    payment_method_id = fields.Many2one(comodel_name="l10n_mx_edi.payment.method", string="Forma de pago")
    payment_amount = fields.Float(string="Monto pagado")
    wizard_id = fields.Many2one(comodel_name="account.payment.report.wizard", string="Wizard de creación")
    iva_amount = fields.Float(string="IVA")
    ieps_amount = fields.Float(string="IEPS")
    iva_ret_amount = fields.Float(string="IVA retenido")
    isr_ret_amount = fields.Float(string="ISR retenido")
    report_type = fields.Selection(string="Tipo de comprobante", selection=[('out','Proveedores'),('in','Clientes')])
    invoice_amount = fields.Float(string="Importe factura")
    subtotal_payment = fields.Float(string="Subtotal pagado")
    rfc_emitter = fields.Char(string="RFC emisor")
    rfc_receiver = fields.Char(string="RFC receptor")