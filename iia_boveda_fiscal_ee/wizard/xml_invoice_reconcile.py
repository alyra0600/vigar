# -*- coding: utf-8 -*-
from odoo import models,fields, api, _
from odoo.exceptions import UserError
import logging
_logger = logging.getLogger(__name__)

class XMLInvoiceReconcile(models.TransientModel):
    _name ='xml.invoice.reconcile'
    _description = 'Conciliación de facturas'
    
    attachment_id = fields.Many2one(comodel_name='ir.attachment', string="Adjunto XML")
    invoice_id = fields.Many2one(comodel_name='account.move', string="Factura")
    payment_id = fields.Many2one(comodel_name='account.payment', string="Pago")
    date = fields.Date(string="Fecha")
    client_name = fields.Char(string="Cliente")
    amount = fields.Float(string="Importe")
    reconcilled = fields.Boolean(string="¿Está conciliado?")
    moneda = fields.Char(string="Moneda")
    folio_fiscal = fields.Char(string="Folio Fiscal")
    folio_factura = fields.Char(string="Folio factura")
    forma_pago = fields.Selection(
        selection=[('01', '01 - Efectivo'), 
                   ('02', '02 - Cheque nominativo'), 
                   ('03', '03 - Transferencia electrónica de fondos'),
                   ('04', '04 - Tarjeta de Crédito'), 
                   ('05', '05 - Monedero electrónico'),
                   ('06', '06 - Dinero electrónico'), 
                   ('08', '08 - Vales de despensa'), 
                   ('12', '12 - Dación en pago'), 
                   ('13', '13 - Pago por subrogación'), 
                   ('14', '14 - Pago por consignación'), 
                   ('15', '15 - Condonación'), 
                   ('17', '17 - Compensación'), 
                   ('23', '23 - Novación'), 
                   ('24', '24 - Confusión'), 
                   ('25', '25 - Remisión de deuda'), 
                   ('26', '26 - Prescripción o caducidad'), 
                   ('27', '27 - A satisfacción del acreedor'), 
                   ('28', '28 - Tarjeta de débito'), 
                   ('29', '29 - Tarjeta de servicios'), 
                   ('30', '30 - Aplicación de anticipos'), 
                   ('31', '31 - Intermediario pagos'), 
                   ('99', '99 - Por definir'),],
        string='Forma de pago',
    )
    uso_cfdi = fields.Selection(
        selection=[('G01', _('Adquisición de mercancías')),
                   ('G02', _('Devoluciones, descuentos o bonificaciones')),
                   ('G03', _('Gastos en general')),
                   ('I01', _('Construcciones')),
                   ('I02', _('Mobiliario y equipo de oficina por inversiones')),
                   ('I03', _('Equipo de transporte')),
                   ('I04', _('Equipo de cómputo y accesorios')),
                   ('I05', _('Dados, troqueles, moldes, matrices y herramental')),
                   ('I06', _('Comunicacion telefónica')),
                   ('I07', _('Comunicación Satelital')),
                   ('I08', _('Otra maquinaria y equipo')),
                   ('D01', _('Honorarios médicos, dentales y gastos hospitalarios')),
                   ('D02', _('Gastos médicos por incapacidad o discapacidad')),
                   ('D03', _('Gastos funerales')),
                   ('D04', _('Donativos')),
                   ('D07', _('Primas por seguros de gastos médicos')),
                   ('D08', _('Gastos de transportación escolar obligatoria')),
                   ('D10', _('Pagos por servicios educativos (colegiaturas)')),
                   ('P01', _('Por definir')),],
        string='Uso CFDI (cliente)',
    )
    numero_cetificado = fields.Char(string="Numero cetificado")
    fecha_certificacion = fields.Char(string="Fecha certificacion")
    selo_digital_cdfi = fields.Char(string="Sello digital CFDI")
    selo_sat = fields.Char(string="Sello SAT")
    tipocambio = fields.Char(string="Tipo cambio")
    tipo_comprobante = fields.Selection(
        selection=[('I', 'Ingreso'), 
                   ('E', 'Egreso'),
                   ('P', 'Pago'),
                   ('N', 'Nomina'),
                    ('T', 'Traslado'),],
        string='Tipo de comprobante',
    )
    fecha_factura = fields.Datetime(string='Fecha Factura')
    number_folio = fields.Char(string='Folio')
    
    def action_reconcile(self):
        self.ensure_one()
        invoice = self.invoice_id
        payment = self.payment_id
        if not invoice and not payment:
            raise UserError(_("Seleccionar primero la factura/pago y posteriormente reconciliar con el XML."))
        if invoice:
            if invoice.amount_total != self.amount:
                raise UserError(_('El total de la factura y el XML son distintos'))
            invoice.write({
                'l10n_mx_edi_cfdi_uuid': self.folio_fiscal,
                'l10n_mx_edi_usage' : self.uso_cfdi,
            })
            self.attachment_id.write({'res_id': invoice.id, 'res_model': invoice._name,})
            _logger.info("Factura conciliada")
            invoice._compute_cfdi_uuid()
            self.write({'reconcilled':True})
        if payment:
            if payment.amount != self.amount:
                raise UserError(_('El total de la factura y el XML son distintos'))
            payment.write({'l10n_mx_edi_cfdi_uuid': self.folio_fiscal,
            })
            self.attachment_id.write({'res_id': payment.id, 'res_model': payment._name})
            self.write({'reconcilled':True})
        return