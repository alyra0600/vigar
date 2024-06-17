from odoo import api, fields, models

class AccountJournal(models.Model):
	_inherit = 'account.journal'

	tipo_de_comprobante_boveda = fields.Selection(selection=[
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
	], string='Tipo de comprobante')