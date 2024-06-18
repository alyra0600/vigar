from odoo import api, fields, models


class CfdiConceptosTaxt(models.Model):
    _name = 'iia_boveda_fiscal.cfdi.concepto.tax'
    _description = u'Impuestos de conceptos de CFDI'
    _check_company_auto = True

    sequence = fields.Integer(string='Secuencia', required=True)
    company_id = fields.Many2one(comodel_name='res.company', string='Empresa', related='iia_boveda_fiscal_cfdi_concepto_id.company_id', readonly=True)
    base = fields.Float(string='Base',  readonly=True)
    impuesto = fields.Char(string='Código', readonly=True)
    tipo_factor = fields.Char(string='Código de porcentaje', readonly=True)
    tasa_cuota = fields.Float(string='Tasa o cuota', readonly=True, digits=(6, 4))
    importe = fields.Float(string='Importe', readonly=True)
    tax_id = fields.Many2one(comodel_name='account.tax', string='Impuesto')
    iia_boveda_fiscal_cfdi_concepto_id = fields.Many2one(comodel_name='iia_boveda_fiscal.cfdi.concepto', string='Concepto de CFDI', required=True, ondelete="cascade")
    iia_boveda_fiscal_cfdi_id = fields.Many2one(comodel_name='iia_boveda_fiscal.cfdi', string='CFDI', related="iia_boveda_fiscal_cfdi_concepto_id.iia_boveda_fiscal_cfdi_id", store=True, ondelete="cascade")
    tax_type = fields.Selection(string="Tipo de impuesto", selection=[('retencion', 'Retención'), ('traslado', 'Traslados')])
