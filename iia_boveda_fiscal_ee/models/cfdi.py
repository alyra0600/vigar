# -*- encoding: utf-8 -*-

from collections import OrderedDict
from datetime import date
import calendar
from odoo import api, fields, models, _, Command
from odoo import (api, fields, models)
from odoo.exceptions import RedirectWarning, ValidationError
import base64
import logging
import os.path
import xmltodict
from os.path import basename
from zipfile import ZipFile
from tempfile import TemporaryDirectory

_logger = logging.getLogger(__name__)

class Cfdi(models.Model):
	_name = 'iia_boveda_fiscal.cfdi'
	_inherit = ['mail.thread', 'mail.activity.mixin']
	_description = 'CFDI'
	_order = 'fecha DESC'
	
	#-------------------------------------------------CAMPOS------------------------------------------------------------
	
	po_count = fields.Integer(compute='_get_po', string='Ordenes de compra', tracking=True)
	code = fields.Char(string='Código', readonly=True)
	uuid = fields.Char(string='UUID', readonly=True)
	attachment_id = fields.Many2one(comodel_name='ir.attachment', string='Archivo adjunto')
	certificado = fields.Char(string='Certificado', readonly=True)
	fecha = fields.Date(string='Fecha', readonly=True)
	folio = fields.Char(string='Folio', readonly=True)
	forma_pago = fields.Char(string='Forma de pago', readonly=True)
	lugar_expedicion = fields.Char(string='Lugar de expedición', readonly=True)
	metodo_pago = fields.Selection(selection=[('PPD', 'PPD'), ('PUE', 'PUE')], string='Método de pago', readonly=True)
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
	],
		string='Tipo de comprobante', index=True, readonly=True, default='SI')
	total = fields.Float(string='Total', readonly=True)
	version = fields.Char(string='Versión', readonly=True)
	condiciones_pago = fields.Char(string='Condiciones de pago', readonly=True)
	company_id = fields.Many2one(comodel_name='res.company', string='Compañía', default=lambda self: self.env.company, readonly=True)
	partner_id_emisor = fields.Many2one(comodel_name='res.partner', string='Emisor', readonly=True)
	partner_id_receptor = fields.Many2one(comodel_name='res.partner', string='Receptor', readonly=True)
	move_id = fields.Many2one(comodel_name='account.move', string='Factura', readonly=True, tracking=True)
	concepto_ids = fields.One2many(comodel_name="iia_boveda_fiscal.cfdi.concepto",inverse_name="iia_boveda_fiscal_cfdi_id", string='Conceptos')
	tax_ids = fields.One2many(comodel_name='iia_boveda_fiscal.cfdi.concepto.tax', inverse_name='iia_boveda_fiscal_cfdi_id', string='Impuestos')
	state = fields.Selection(selection=[
		('draft', 'Borrador'),
		('done', 'Procesada'),
		('cancel', 'Anulado')],
		string='Estado', required=True, copy=False, default='draft', tracking=True)
	real_state = fields.Selection(selection=[
		('draft', 'Borrador'),
		('done', 'Procesada'),
		('cancel', 'Anulado')],
		string='Estado Auto', compute='_compute_state')
	payable_account_id = fields.Many2one(comodel_name='account.account', string='Cuenta contable a pagar', tracking=True)
	account_id = fields.Many2one(comodel_name='account.account', string='Cuenta contable gasto', tracking=True)
	account_analytic_account_id = fields.Many2one(comodel_name='account.analytic.account', string='Cuenta analítica')
	analytic_distribution = fields.Json(string="Distribución analítica")
	analytic_precision = fields.Integer(string="Precisión analítica", store=False,	default=lambda self: self.env['decimal.precision'].precision_get("Percentage Analytic"))
	fiscal_position_id = fields.Many2one(comodel_name='account.fiscal.position', string='Posicion fiscal')
	journal_id = fields.Many2one(comodel_name='account.journal', string='Diario', readonly=False, tracking=True)
	tax_isr_id = fields.Many2one(comodel_name='account.tax', string=u'Retención ISR')
	tax_iva_id = fields.Many2one(comodel_name='account.tax', string=u'Retención IVA')
	observations = fields.Text(string='Notas')
	estado_sat = fields.Selection(selection=[('Vigente', 'Vigente'), ('Cancelado', 'Cancelado'), ('No Encontrado', 'No Encontrado')],string='Estado SAT', default='Vigente', tracking=True)
	tax_paymnent_ids = fields.One2many("account.cfdi.payment.tax", "cfdi_id", string="Impuestos pagados")
	
	_sql_constraints = [('UK_uuid', 'check(1=1)', 'No error')]
	
	#---------------------------------------------------Metodos---------------------------------------------------------
	
	@api.model
	def create(self, vals_list):
		res = super().create(vals_list)
		for cfdi in res.filtered(lambda move: move.move_id):
			cfdi.move_id.update({
				"cfdi_id": cfdi.id
			})
		return res
	
	@api.depends(lambda self: (self._rec_name,) if self._rec_name else ())
	def _compute_display_name(self):
		for record in self:
			folio = f"[{record.serie}-{record.folio}] - " if record.serie and record.folio else f"[{record.serie}] - " if record.serie and not record.folio else f"[{record.folio}] - " if not record.serie and record.folio else ""
			name = f"{folio}" + record.uuid + ' - $' + str(record.total)
			record.display_name = name
	
	#Abrir la orden de compra creada
	def action_open_purchase_order(self):
		tree_id = self.env.ref("purchase.purchase_order_kpis_tree").id
		form_id = self.env.ref("purchase.purchase_order_form").id
		return {
			"name": _("Cotización de compra"),
			"view_mode": "tree,form",
			'views': [(tree_id, 'tree'), (form_id, 'form')],
			"res_model": "purchase.order",
			"domain": [('cfdi_origin_id', '=', self.id)],
			"type": "ir.actions.act_window",
			"target": "current",
		}
	
	#Abrir factura relacionada al CFDI
	def action_open_invoice(self):
		return {
			"name": _("Factura"),
			"view_mode": "form",
			"res_model": "account.move",
			"res_id": self.move_id.id,
			"type": "ir.actions.act_window",
			"target": "current",
		}
	
	#Obtención de las ordenes de compra relacionadas al CFDI
	def _get_po(self):
		for orders in self:
			purchase_ids = self.env['purchase.order'].sudo().search([('cfdi_origin_id', '=', orders.id)])
			orders.po_count = len(purchase_ids)
	
	# Crear los cfdis a partir de los xml
	# ('I', 'Facturas de clientes')
	# ('SI', 'Facturas de proveedor')
	# ('E', 'Notas de crédito clientes')
	# ('SE', 'Notas de crédito proveedor')
	# ('P', 'REP de clientes') Pago de clientes
	# ('SP', 'REP de proveedores'), Pagos de proveedores
	# ('N', 'Nominas de empleados')
	# ('SN', 'Nómina propia')
	# ('T', 'Factura de traslado cliente')
	# ('ST', 'Factura de traslado proveedor')
	def create_cfdis(self, attachment_data):
		cfdi_list = []
		cfdi_ids = self.env["iia_boveda_fiscal.cfdi"]
		uuids = []
		for data in attachment_data:
			# Obtener la información para crear el cfdi
			xml_data = self.get_cfdi_data(data.get("datas"))
			if xml_data.get("Comprobante"):
				cfdi_type = self.get_cfdi_type(xml_data)
				uuid = self.validation_cfdi(xml_data, cfdi_type)
				#Evitar UUID repetidos ya que el SAT manda en ocasiones el mismo XML dos veces
				if uuid and uuid not in uuids:
					uuids.append(uuid)
					emiiter_partner_id, recipient_partner_id = self.get_cfdi_partners(xml_data)
					move_id = self.validate_cfdi_move(xml_data, uuid, cfdi_type, emiiter_partner_id)
					cfdi_data = self.add_cfdi_data(xml_data, uuid, emiiter_partner_id, recipient_partner_id, move_id, cfdi_type, data)
					cfdi_data = self.get_cfdi_lines(xml_data, cfdi_data, cfdi_type, emiiter_partner_id,	recipient_partner_id)
					cfdi_data = self.get_payment_tax(cfdi_type, xml_data, cfdi_data)
					cfdi_list.append(cfdi_data)
				else:
					continue
			else:
				continue
		if cfdi_list:
			cfdi_ids = self.env["iia_boveda_fiscal.cfdi"].sudo().create(cfdi_list)
		return cfdi_ids
	
	# Obtener la información del xml
	def get_cfdi_data(self, xml_file):
		file_content = base64.b64decode(xml_file)
		if b'xmlns:schemaLocation' in file_content and not b'xsi:schemaLocation' in file_content:
			file_content = file_content.replace(b'xmlns:schemaLocation', b'xsi:schemaLocation')
		file_content = file_content.replace(b'cfdi:', b'')
		file_content = file_content.replace(b'tfd:', b'')
		try:
			xml_data = xmltodict.parse(file_content)
			return xml_data
		except Exception as e:
			_logger.info(e)
			return dict()
	
	# Validaciones antes de la creación del CFDI
	def validation_cfdi(self, xml_data, cfdi_type):
		if '@UUID' in xml_data['Comprobante']['Complemento']['TimbreFiscalDigital']:
			uuid = xml_data['Comprobante']['Complemento']['TimbreFiscalDigital']['@UUID']
			cfdi_id = self.env['iia_boveda_fiscal.cfdi'].sudo().search([('uuid', '=', uuid)], limit=1)
			if cfdi_id:
				_logger.info(f"El CFDI con UUID {uuid}, ya existe en la base de datos, se omitirá en el proceso.")
				return False
			#Evitar que se suban xml que no pertenecen a la empresa
			if "S" in cfdi_type:
				partner_rfc = xml_data['Comprobante']['Receptor']['@Rfc']
			else:
				partner_rfc = xml_data['Comprobante']['Emisor']['@Rfc']
			if partner_rfc != self.env.company.vat:
				return False
		else:
			return False
		return uuid
	
	# Obtener el tipo de comprobante que es el CFDI
	def get_cfdi_type(self, xml_data):
		cfdi_type = xml_data['Comprobante']['@TipoDeComprobante'] if '@TipoDeComprobante' in xml_data['Comprobante'] else 'I'
		if cfdi_type in ['I', 'E', 'P']:
			if xml_data['Comprobante']['Emisor']['@Rfc'] != self.env.company.vat:
				cfdi_type = 'S' + cfdi_type
		return cfdi_type
	
	# Obtener el emisor y receptor del cfdi
	def get_cfdi_partners(self, xml_data):
		emitter_partner_id = self.env['res.partner'].sudo().search([('vat', '=', xml_data['Comprobante']['Emisor']['@Rfc'])],	limit=1)
		recipient_partner_id = self.env['res.partner'].sudo().search([('vat', '=', xml_data['Comprobante']['Receptor']['@Rfc'])], limit=1)
		if not emitter_partner_id:
			emitter_partner_id = self.create_cfdi_partner(xml_data, "Emisor")
		if not recipient_partner_id:
			recipient_partner_id = self.create_cfdi_partner(xml_data, "Receptor")
		return emitter_partner_id, recipient_partner_id
	
	# Crear los contactos del CFDI si es necesario
	def create_cfdi_partner(self, xml_data, partner_type):
		data = {
			'name': xml_data['Comprobante'][partner_type]['@Nombre'],
			'vat': xml_data['Comprobante'][partner_type]['@Rfc'],
			'l10n_mx_edi_fiscal_regime': xml_data['Comprobante'][partner_type][
				'@RegimenFiscal'] if partner_type == "Emisor" else xml_data['Comprobante'][partner_type][
				'@RegimenFiscalReceptor'],
			'country_id': self.env.company.country_id.id,
			'company_type': 'company'
		}
		partner_id = self.env["res.partner"].create(data)
		return partner_id
	
	# Buscar el asiento contable de odoo relacionado si es que existe
	def validate_cfdi_move(self, xml_data, uuid, cfdi_type, emitter_partner_id):
		move_id = self.env["account.move"]
		if cfdi_type in ["I", "E"]:
			move_id = move_id.sudo().search([("move_type", "in", ["out_invoice", "out_refund"]), ("l10n_mx_edi_cfdi_uuid", "=", uuid),("state","=","posted"), ("cfdi_id","=", False)], limit=1)
		elif cfdi_type in ["SI", "SE"]:
			folio = xml_data['Comprobante']['@Folio'] if '@Folio' in xml_data['Comprobante'] else ''
			move_id = self.env['account.move'].sudo().search([('partner_id', '=', emitter_partner_id.id), ('ref', 'ilike', folio), ('move_type', 'in', ['in_invoice', 'in_refund']),("cfdi_id","=",False),("state","=","posted"), ("cfdi_id","=", False)], limit=1)
			if not move_id:
				if '@Serie' in xml_data['Comprobante']:
					folio = xml_data['Comprobante']['@Serie'] + folio
					move_id = self.env['account.move'].sudo().search([('partner_id', '=', emitter_partner_id.id), ('ref', '=', folio), ('move_type', 'in', ['in_invoice', 'in_refund']),("cfdi_id","=",False),("state","=","posted")], limit=1)
				if not move_id:
					amount_untaxed = xml_data['Comprobante']['@SubTotal'] if '@SubTotal' in xml_data['Comprobante'] else 0
					invoice_date = xml_data['Comprobante']['@Fecha'] if '@Fecha' in xml_data['Comprobante'] else ""
					move_id = self.env['account.move'].sudo().search([('partner_id', '=', emitter_partner_id.id), ('move_type', 'in', ['in_invoice']),("cfdi_id","=",False),("state","=","posted"),("amount_untaxed","=",amount_untaxed),("invoice_date","=",invoice_date[:10])], limit=1)
		return move_id
	
	# Preparar la informacion del CFDI
	def add_cfdi_data(self, xml_data, uuid, emitter_partner_id, recipient_partner_id, move_id, cfdi_type, attachment_data):
		journal_id, account_id = self.get_cfdi_journal_id(cfdi_type, emitter_partner_id, recipient_partner_id)
		partner_id = recipient_partner_id if cfdi_type in ["I", "E"] else emitter_partner_id
		payable_account_id = self.get_payable_cfdi_account_id(cfdi_type, partner_id)
		attachment_id = self.env["ir.attachment"].sudo().create(attachment_data)
		data = {
			"attachment_id": attachment_id.id,
			"code": uuid,
			"uuid": uuid,
			"certificado": xml_data['Comprobante']['@Certificado'] if '@Certificado' in xml_data['Comprobante'] else '',
			"fecha": xml_data['Comprobante']['@Fecha'] if '@Fecha' in xml_data['Comprobante'] else '',
			"folio": xml_data['Comprobante']['@Folio'] if '@Folio' in xml_data['Comprobante'] else '',
			"forma_pago": xml_data['Comprobante']['@FormaPago'] if '@FormaPago' in xml_data['Comprobante'] else '',
			"lugar_expedicion": xml_data['Comprobante']['@LugarExpedicion'] if '@LugarExpedicion' in xml_data['Comprobante'] else '',
			"metodo_pago": xml_data['Comprobante']['@MetodoPago'] if '@MetodoPago' in xml_data['Comprobante'] else '',
			"moneda": xml_data['Comprobante']['@Moneda'] if '@Moneda' in xml_data['Comprobante'] else '',
			"no_certificado": xml_data['Comprobante']['@NoCertificado'] if '@NoCertificado' in xml_data['Comprobante'] else '',
			"sello": xml_data['Comprobante']['@Sello'] if '@Sello' in xml_data['Comprobante'] else '',
			"serie": xml_data['Comprobante']['@Serie'] if '@Serie' in xml_data['Comprobante'] else '',
			"subtotal": xml_data['Comprobante']['@SubTotal'] if '@SubTotal' in xml_data['Comprobante'] else '',
			"tipo_de_comprobante": cfdi_type,
			"total": xml_data['Comprobante']['@Total'] if '@Total' in xml_data['Comprobante'] else '',
			"version": xml_data['Comprobante']['@Version'] if '@Version' in xml_data['Comprobante'] else '',
			"condiciones_pago": xml_data['Comprobante']['@CondicionesDePago'] if '@CondicionesDePago' in xml_data['Comprobante'] else '',
			"partner_id_emisor": emitter_partner_id.id,
			"partner_id_receptor": recipient_partner_id.id,
			"move_id": move_id.id if move_id else False,
			"state": "draft" if not move_id else "done",
			"journal_id": journal_id.id if journal_id else False,
			"account_id": account_id.id if account_id else False,
			"fiscal_position_id": partner_id.property_account_position_id.id if partner_id.property_account_position_id else False,
			"tax_iva_id": partner_id.tax_iva_id.id if partner_id.tax_iva_id else False,
			"tax_isr_id": partner_id.tax_isr_id.id if partner_id.tax_isr_id else False,
			"payable_account_id": payable_account_id.id if payable_account_id else False
		}
		return data
	
	# Obteniendo el diario contable dependiendo del tipo de comprobante
	def get_cfdi_journal_id(self, cfdi_type, emitter_partner_id, recipient_partner_id):
		journal_id = self.env['account.journal'].sudo().search([('tipo_de_comprobante_boveda', '=', cfdi_type), ("company_id.id", "=", self.env.company.id)], limit=1)
		#Buscamos si ya hubo un CFDI al mismo cliente y receptor y del mismo tipo y que tenga un diario colocado
		if not journal_id:
			cfdi_id = self.env["iia_boveda_fiscal.cfdi"].sudo().search([("partner_id_emisor.id","=",emitter_partner_id.id),("partner_id_receptor.id","=",recipient_partner_id.id),("tipo_de_comprobante","=",cfdi_type),("journal_id","!=",False)], limit=1)
			journal_id = cfdi_id.journal_id if cfdi_id else False
		account_id = journal_id.default_account_id if journal_id and journal_id.default_account_id else False
		if not account_id:
			partner_id = recipient_partner_id if cfdi_type in ["I", "E"] else emitter_partner_id
			account_id = self.get_expense_cfdi_account_id(cfdi_type, partner_id)
		return journal_id, account_id
	
	# Obtener cuenta por pagar dependiendo del tipo de comprobante
	def get_payable_cfdi_account_id(self, cfdi_type, partner_id):
		#Se busca si se tiene configurado la cuenta por pagar en la cuenta sino se busca por el contacto y por ultimo se busca un cfdi con el mismo contacto y tipo
		payable_account_id = self.env['account.account'].sudo().search([('tipo_de_comprobante_boveda', '=', cfdi_type), ("company_id.id", "=", self.env.company.id)], limit=1)
		if not payable_account_id and partner_id:
			payable_account_id = partner_id.property_account_payable_id
			#Buscamos un CFDI parecido para obtener la cuenta por pagar
			if not payable_account_id and cfdi_type in ['I','E']:
				cfdi_id = self.env["iia_boveda_fiscal.cfdi"].sudo().search([("partner_id_receptor.id", "=", partner_id.id), ("tipo_de_comprobante", "=", cfdi_type), ("payable_account_id", "!=", False)], limit=1)
				payable_account_id = cfdi_id.payable_account_id if cfdi_id else False
			elif not payable_account_id and cfdi_type in ['SI','SE']:
				cfdi_id = self.env["iia_boveda_fiscal.cfdi"].sudo().search([("partner_id_emisor.id", "=", partner_id.id), ("tipo_de_comprobante", "=", cfdi_type), ("payable_account_id", "!=", False)], limit=1)
				payable_account_id = cfdi_id.payable_account_id if cfdi_id else False
		return payable_account_id
	
	#Obtener la cuenta de gastos
	def get_expense_cfdi_account_id(self, cfdi_type, partner_id):
		if partner_id:
			expense_account_id = partner_id.account_xml_id
			#Buscamos un CFDI parecido para obtener la cuenta por pagar
			if not expense_account_id and cfdi_type in ['I','E']:
				cfdi_id = self.env["iia_boveda_fiscal.cfdi"].sudo().search([("partner_id_receptor.id", "=", partner_id.id), ("tipo_de_comprobante", "=", cfdi_type), ("account_id", "!=", False)], limit=1)
				expense_account_id = cfdi_id.payable_account_id if cfdi_id else False
			elif not expense_account_id and cfdi_type in ['SI','SE']:
				cfdi_id = self.env["iia_boveda_fiscal.cfdi"].sudo().search([("partner_id_emisor.id", "=", partner_id.id), ("tipo_de_comprobante", "=", cfdi_type), ("account_id", "!=", False)], limit=1)
				expense_account_id = cfdi_id.payable_account_id if cfdi_id else False
		return expense_account_id
	
	# Se obtienen las lineas de CFDI
	def get_cfdi_lines(self, xml_data, cfdi_data, cfdi_type, emitter_partner_id, recipient_partner_id):
		if type(xml_data['Comprobante']['Conceptos']['Concepto']) is list:
			lines = xml_data['Comprobante']['Conceptos']['Concepto']
		elif type(xml_data['Comprobante']['Conceptos']['Concepto']) is OrderedDict:
			lines = xml_data['Comprobante']['Conceptos'].items()
		else:
			lines = [xml_data['Comprobante']['Conceptos']['Concepto']]
		i = 1
		data_list = []
		for line_value in lines:
			if type(xml_data['Comprobante']['Conceptos']['Concepto']) is list:
				line = line_value
			elif type(xml_data['Comprobante']['Conceptos']['Concepto']) is OrderedDict:
				line = line_value[1]
			else:
				line = line_value
			if float(line['@Importe']) >= 0:
				uom_id = False
				if '@ClaveUnidad' in line:
					uom_unspsc_id = self.env['product.unspsc.code'].sudo().search([('code', '=', line['@ClaveUnidad'])])
					if uom_unspsc_id:
						uom_id = self.env['uom.uom'].sudo().search([('unspsc_code_id', '=', uom_unspsc_id.id)], limit=1)
				if uom_id:
					unidad_id = uom_id.id
				else:
					unidad_id = False
				product_category_id = False
				if '@ClaveProdServ' in line:
					unspsc_product_category_id = self.env['product.unspsc.code'].sudo().search(
						[('code', '=', line['@ClaveProdServ'])])
					if unspsc_product_category_id:
						product_category_id = unspsc_product_category_id.id
					else:
						product_category_id = False
				
				data_line = {
					'sequence': i,
					'code_cfdi': cfdi_data.get("code"),
					'fecha': cfdi_data.get("fecha"),
					'folio': cfdi_data.get("folio"),
					'forma_pago': cfdi_data.get("forma_pago"),
					'lugar_expedicion': cfdi_data.get("lugar_expedicion"),
					'metodo_pago': cfdi_data.get("metodo_pago"),
					'moneda': cfdi_data.get("moneda"),
					'no_certificado': cfdi_data.get("no_certificado"),
					'sello': cfdi_data.get("sello"),
					'serie': cfdi_data.get("serie"),
					'subtotal': cfdi_data.get("subtotal"),
					'tipo_de_comprobante': cfdi_data.get("tipo_de_comprobante"),
					'total': cfdi_data.get("total"),
					'version': cfdi_data.get("version"),
					'partner_id_emisor': cfdi_data.get("partner_id_emisor"),
					'partner_id_receptor': cfdi_data.get("partner_id_receptor"),
					'clave_prod_serv': line['@ClaveProdServ'] if '@ClaveProdServ' in line else '',
					'no_identificacion': line['@NoIdentificacion'] if '@NoIdentificacion' in line else '',
					'cantidad': float(line['@Cantidad']),
					'clave_unidad': line['@ClaveUnidad'] if '@ClaveUnidad' in line else '',
					'unidad': line['@Unidad'] if '@Unidad' in line else '',
					'descripcion': line['@Descripcion'],
					'descuento': float(line['@Descuento']) if '@Descuento' in line else 0,
					'valor_unitario': float(line['@ValorUnitario']),
					'uom_id': unidad_id,
					'unspsc_product_category_id': product_category_id,
					'importe': float(line['@Importe']),
				}
				data_line = self.search_cfdi_product(line, cfdi_type, data_line, emitter_partner_id, recipient_partner_id)
				data_line = self.get_cfdi_tax_lines(data_line, line, cfdi_type, recipient_partner_id)
				data_list.append(Command.create(data_line))
			i += 1
		if data_list:
			cfdi_data["concepto_ids"] = data_list
		return cfdi_data
	
	def search_cfdi_product(self, line, cfdi_type, data_line, emitter_partner_id, recipient_partner_id):
		partner_id = recipient_partner_id if cfdi_type in ["I", "E"] else emitter_partner_id
		product_tmpl_id = self.env['product.template']
		concept_id = self.env['iia_boveda_fiscal.cfdi.concepto']
		account_line_id = self.env['account.move.line']
		# Buscar el producto para poder relacionarlo a la linea del concepto
		if '@NoIdentificacion' in line:
			# Si el comprobante es una factura de proveedor o una nota de cliente del proveedor
			if cfdi_type in ['SI', 'SE']:
				# Se busca si es que se cuenta con una lista de precios a proveedor que identifique el producto mediante el codigo del producto
				product_supplier_id = self.env['product.supplierinfo'].sudo().search([('partner_id', '=', partner_id.id), ('product_code', '=', line['@NoIdentificacion'])], limit=1)
				if product_supplier_id:
					product_tmpl_id = product_supplier_id.product_tmpl_id
			if not product_tmpl_id and cfdi_type in ["I","E"]:
				product_tmpl_id = self.env['product.template'].sudo().search([('default_code', '=', line['@NoIdentificacion'])], limit=1)
		# Identificar si se tiene registro de algun producto que coincida exactamente con la descripción del concepto
		if not product_tmpl_id and '@Descripcion' in line:
			if cfdi_type in ['SI', 'SE']:
				product_supplier_id = self.env['product.supplierinfo'].sudo().search([('partner_id', '=', partner_id.id), ('product_name', '=', line['@Descripcion'])], limit=1)
				if product_supplier_id:
					product_tmpl_id = product_supplier_id.product_tmpl_id
			elif cfdi_type in ['I', 'E']:
				product_tmpl_id = self.env['product.template'].sudo().search(['|', ("name", "=", line['@Descripcion']), ('default_code', '=', line['@Descripcion'])], limit=1)
		# Se busca el producto si ya ha habido lineas de producto con el mismo emisor y misma clave de producto o descripcion
		if not product_tmpl_id and '@ClaveProdServ' in line and partner_id:
			concept_id = self.env['iia_boveda_fiscal.cfdi.concepto'].sudo().search([("product_tmpl_id", "!=", False), ("partner_id_emisor.id", "=", partner_id.id if cfdi_type in ["SI","SE"] else emitter_partner_id.id),("clave_prod_serv", "=", line['@ClaveProdServ']), ("company_id.id", "=", self.env.company.id)], limit=1)
			if concept_id:
				product_tmpl_id = concept_id.product_tmpl_id
			else:
				account_line_id = self.env["account.move.line"].sudo().search([("product_id", "!=", False), ("product_id.unspsc_code_id.code", "=", line['@ClaveProdServ']), ("partner_id.id", "=", partner_id.id)], limit=1)
				if account_line_id:
					product_tmpl_id = account_line_id.product_id.product_tmpl_id
		# Identificar si existen lineas de conceptos que coincidan con la misma descripción y del mismo emisor
		if not product_tmpl_id and '@Descripcion' in line and partner_id:
			concept_id = self.env['iia_boveda_fiscal.cfdi.concepto'].sudo().search([("product_tmpl_id", "!=", False), ("partner_id_emisor.id", "=", partner_id.id if cfdi_type in ["SI", "SE"] else emitter_partner_id.id), ("descripcion", "=", line['@Descripcion']), ("company_id.id", "=", self.env.company.id)], limit=1)
			if concept_id:
				product_tmpl_id = concept_id.product_tmpl_id
		if not product_tmpl_id and partner_id and partner_id.product_tmpl_id:
			product_tmpl_id = partner_id.product_tmpl_id
		
		if product_tmpl_id:
			product_id = self.env['product.product'].sudo().search([('product_tmpl_id', '=', product_tmpl_id.id)],limit=1)
			data_line["product_id"] = product_id.id if product_id else False
			data_line["product_tmpl_id"] = product_tmpl_id.id
			categ_id = product_tmpl_id.categ_id
			if cfdi_type in ["SI","SE"]:
				account_id = product_tmpl_id.property_account_expense_id if product_tmpl_id.property_account_expense_id else categ_id.property_account_expense_categ_id if categ_id else False
			elif cfdi_type in ["I","E"]:
				account_id = product_tmpl_id.property_account_income_id if product_tmpl_id.property_account_income_id else categ_id.property_account_income_categ_id if categ_id else False
			data_line["account_id"] = concept_id.account_id.id if concept_id and concept_id.account_id else account_line_id.account_id.id if account_line_id else account_id.id if account_id else False
		return data_line
	
	# Se obtienen los impuestos del CFDI
	def get_cfdi_tax_lines(self, data_line, line, cfdi_type, recipient_partner_id):
		tax_list = []
		if 'Impuestos' in line:
			j = 1
			if 'Traslados' in line['Impuestos']:
				if type(line['Impuestos']['Traslados']['Traslado']) is list:
					impuestos = line['Impuestos']['Traslados']['Traslado']
				elif type(line['Impuestos']['Traslados']['Traslado']) is OrderedDict:
					impuestos = line['Impuestos']['Traslados'].items()
				else:
					impuestos = [line['Impuestos']['Traslados']['Traslado']]
				for value_tax in impuestos:
					if type(line['Impuestos']['Traslados']['Traslado']) is list:
						impuesto = value_tax
					elif type(line['Impuestos']['Traslados']['Traslado']) is OrderedDict:
						impuesto = value_tax[1]
					else:
						impuesto = value_tax
					if str(impuesto['@TipoFactor']).strip().upper() == 'EXENTO':
						tasa_o_cuota = 0
						importe = 0
					else:
						tasa_o_cuota = float(impuesto['@TasaOCuota'])
						importe = float(impuesto['@Importe'])
					tax_data = {
						'sequence': j,
						'base': float(impuesto['@Base']),
						'impuesto': impuesto['@Impuesto'],
						'tipo_factor': impuesto['@TipoFactor'],
						'tasa_cuota': tasa_o_cuota,
						'importe': importe,
						'tax_type': 'traslado'
					}
					j = j + 1
					amount = tasa_o_cuota * 100
					tax_domain = [('amount', '=', amount), ('company_id', '=', self.env.company.id)]
					t_id = self.env["account.tax"]
					if tax_data.get("impuesto") == '002':
						tax_domain.append(("l10n_mx_tax_type", "=", "iva"))
					elif tax_data.get("impuesto") == '003':
						tax_domain.append(("l10n_mx_tax_type", "=", "ieps"))
					elif tax_data.get("impuesto") == '001':
						tax_domain.append(("l10n_mx_tax_type", "=", "isr"))
					
					if cfdi_type in ['I', 'E']:
						tax_domain.append(('type_tax_use', '=', 'sale'))
						t_id = self.env['account.tax'].sudo().search(tax_domain, limit=1)
					elif cfdi_type in ['SI', 'SE']:
						tax_domain.append(('type_tax_use', '=', 'purchase'))
						t_id = self.env['account.tax'].sudo().search(tax_domain, limit=1)
					if t_id:
						tax_data["tax_id"] = t_id.id
					tax_list.append(Command.create(tax_data))
			
			if 'Retenciones' in line['Impuestos']:
				if type(line['Impuestos']['Retenciones']['Retencion']) is list:
					retenciones = line['Impuestos']['Retenciones']['Retencion']
				elif type(line['Impuestos']['Retenciones']['Retencion']) is OrderedDict:
					retenciones = line['Impuestos']['Retenciones'].items()
				else:
					retenciones = [line['Impuestos']['Retenciones']['Retencion']]
				for value_tax in retenciones:
					if type(line['Impuestos']['Retenciones']['Retencion']) is list:
						retencion = value_tax
					elif type(line['Impuestos']['Retenciones']['Retencion']) is OrderedDict:
						retencion = value_tax[1]
					else:
						retencion = value_tax
					tasa_o_cuota = float(retencion['@TasaOCuota'])
					importe = float(retencion['@Importe'])
					tax_data = {
						'sequence': j,
						'base': float(retencion['@Base']),
						'impuesto': retencion['@Impuesto'],
						'tipo_factor': retencion['@TipoFactor'],
						'tasa_cuota': tasa_o_cuota,
						'importe': importe,
						'tax_type': 'retencion'
					}
					j = j + 1
					
					amount = round(-(tasa_o_cuota * 100), 2)
					tax_domain = [('amount', '=', amount), ('company_id', '=', self.env.company.id)]
					t_id = self.env['account.tax']
					if tax_data.get("impuesto") == '002':
						tax_domain.append(("l10n_mx_tax_type", "=", "iva"))
					elif tax_data.get("impuesto") == '003':
						tax_domain.append(("l10n_mx_tax_type", "=", "ieps"))
					elif tax_data.get("impuesto") == '001':
						tax_domain.append(("l10n_mx_tax_type", "=", "isr"))
					if cfdi_type in ['I', 'E']:
						tax_domain.append(('type_tax_use', '=', 'sale'))
						t_id = self.env['account.tax'].sudo().search(tax_domain, limit=1)
					elif cfdi_type in ['SI', 'SE']:
						tax_domain.append(('type_tax_use', '=', 'purchase'))
						t_id = self.env['account.tax'].sudo().search(tax_domain, limit=1)
					if t_id:
						tax_data["tax_id"] = t_id.id
					
					if not t_id and cfdi_type in ['SI', 'SE']:
						if tax_data.get("impuesto") == '001':
							if recipient_partner_id.tax_isr_id:
								tax_data["tax_id"] = recipient_partner_id.tax_isr_id.id
						elif tax_data.get("impuesto") == '002':
							if recipient_partner_id.tax_iva_id:
								tax_data["tax_id"] = recipient_partner_id.tax_iva_id.id
					tax_list.append(Command.create(tax_data))
			if tax_list:
				data_line["tax_ids"] = tax_list
		return data_line
	
	def get_payment_tax(self, cfdi_type, xml_data, cfdi_data):
		if cfdi_type in ['P', 'SP']:
			payment_tax_list = []
			payments_list = xml_data['Comprobante']['Complemento']['pago20:Pagos']['pago20:Pago']
			payments_list = self.get_data_iterable(payments_list)
			if payments_list:
				for payment_list in payments_list:
					payment_date = payment_list["@FechaPago"][:10],
					payments = payment_list["pago20:DoctoRelacionado"]
					payments = self.get_data_iterable(payments)
					
					if payments:
						for payment in payments:
							if payment.get("@ObjetoImpDR") and payment.get("@ObjetoImpDR") == '02':
								payment_taxes = payment["pago20:ImpuestosDR"]["pago20:TrasladosDR"]["pago20:TrasladoDR"]
								payment_taxes = self.get_data_iterable(payment_taxes)
								if payment_taxes:
									for payment_tax in payment_taxes:
										payment_tax_data = {
											"name": payment["@IdDocumento"],
											"serie": payment.get("@Serie"),
											"folio": payment.get("@Folio"),
											"currency": payment["@MonedaDR"],
											"currency_rate": payment["@EquivalenciaDR"],
											"paid_amount": payment["@ImpPagado"],
											"previous_balance": payment["@ImpSaldoAnt"],
											"current_balance": payment["@ImpSaldoInsoluto"],
											"subject_tax": payment["@ObjetoImpDR"],
											"payment_date": payment_date[0],
											"tax_amount": payment_tax.get("@ImporteDR"),
											"base_amount": payment_tax["@BaseDR"],
											"type_tax": payment_tax["@ImpuestoDR"],
											"base_tax": float(payment_tax["@TasaOCuotaDR"]) * 100 if payment_tax.get("@TasaOCuotaDR") else 0,
											"exempt_tax": True if payment_tax.get("@TipoFactorDR") == 'Exento' else False,
										}
										payment_tax_list.append(Command.create(payment_tax_data))
			if payment_tax_list:
				cfdi_data["tax_paymnent_ids"] = payment_tax_list
		return cfdi_data
	
	#Procesar los CFDI seleccionados
	def action_done(self):
		self = self.with_user(1)
		invoice_list = []
		folio_names = []
		for rec in self.filtered(lambda cfdi: not cfdi.move_id and cfdi.attachment_id and cfdi.tipo_de_comprobante in ["SI","I"]):
			cfdi_type = rec.tipo_de_comprobante
			partner_id = rec.partner_id_emisor if cfdi_type == "SI" else rec.partner_id_receptor
			folio = f"{rec.serie}-{rec.folio}" if rec.serie and rec.folio else f"{rec.serie}" if rec.serie and not rec.folio else f"{rec.folio}" if not rec.serie and rec.folio else ''
			invoice_data = {
				'move_type': 'in_invoice' if cfdi_type == 'SI' else 'out_invoice' if cfdi_type == 'I' else '',
				'partner_id': partner_id.id,
				'date': rec.fecha,
				'invoice_date': rec.fecha,
				'invoice_date_due': rec.fecha,
				'fiscal_position_id': partner_id.property_account_position_id.id if partner_id.property_account_position_id else rec.fiscal_position_id.id,
				'ref': folio,
				'amount_total_signed': rec.total,
				'amount_total': rec.total,
				'journal_id': rec.journal_id.id,
				'company_id': rec.company_id.id,
				'cfdi_id': rec.id,
				'l10n_mx_edi_cfdi_uuid_cusom': rec.uuid
			}
			if folio != '' and not self.env["account.move"].sudo().search([("name","=",folio),("state","=","posted")],limit=1) and folio not in folio_names and cfdi_type == "I":
				invoice_data["name"] = folio
			folio_names.append(folio)
			i = 1
			line_list = []
			for line in rec.concepto_ids:
				if float(line.importe) > 0:
					data_line = {
						'sequence': i,
						'name': line.descripcion,
						'quantity': float(line.cantidad),
						'product_uom_id': line.uom_id.id,
						'discount': (float(line.descuento) * 100) / float(line.importe),
						'price_unit': float(line.valor_unitario),
						'tax_ids': line.mapped("tax_ids.tax_id").ids,
						'account_id': line.account_id.id if line.account_id else rec.account_id.id if rec.account_id else False,
						'analytic_distribution': rec.analytic_distribution,
						'partner_id': partner_id.id,
					}
					
					if line.product_tmpl_id:
						product_id = self.env['product.product'].sudo().search([('product_tmpl_id', '=', line.product_tmpl_id.id)], limit=1)
						data_line["product_id"] = product_id.id
					line_list.append(Command.create(data_line))
					i = i + 1
			invoice_data["invoice_line_ids"] = line_list
			invoice_list.append(invoice_data)
		invoice_ids = self.env['account.move'].with_context(check_move_validity=False).sudo().create(invoice_list)
		
		for invoice_id in invoice_ids:
			attachment_id = invoice_id.cfdi_id.attachment_id
			invoice_id.cfdi_id.write({
				"move_id": invoice_id.id,
				"state": "done"
			})
			attachment_id.write({
				'res_model': 'account.move',
				'res_id': invoice_id.id,
			})
			if invoice_id.move_type == "out_invoice":
				if self.attachment_id:
					self.attachment_id.sudo().write({
						'res_model': 'account.move',
						'res_id': invoice_id.id,
					})
					if len(invoice_id.l10n_mx_edi_document_ids) == 0:
						create_edi = self.env['l10n_mx_edi.document'].sudo().create({
							'attachment_id': self.attachment_id.id,
							'invoice_ids': invoice_id.ids,
							'move_id': invoice_id.id,
							'state': 'invoice_sent',
							'datetime': invoice_id.create_date
						})
						invoice_id.write({
							'l10n_mx_edi_document_ids': [(6, False, [create_edi.id])],
							'l10n_mx_edi_cfdi_uuid': invoice_id.l10n_mx_edi_cfdi_uuid_cusom,
							'state': 'posted'
						})
					# Se colocaria la factura como timbrada
					elif invoice_id.l10n_mx_edi_document_ids:
						data = {
							'move_id': invoice_id.id,
							'invoice_ids': invoice_id.ids,
							'attachment_id': attachment_id.id,
							'state': 'invoice_sent',
							'datetime': invoice_id.create_date
						}
						self.env["l10n_mx_edi.document"].sudo().create([data])
						invoice_id.write({
							'l10n_mx_edi_cfdi_uuid': invoice_id.l10n_mx_edi_cfdi_uuid_cusom
						})
			invoice_id.write({"state": "posted"})
		return {
			"name": _("Facturas"),
			"view_mode": "tree,form",
			"res_model": "account.move",
			"type": "ir.actions.act_window",
			"target": "current",
			"domain": [('id', 'in', invoice_ids.ids)]
		}
	
	
	def _compute_state(self):
		for record in self:
			record.observations = 'No'
			record.real_state = 'draft'
			if record.move_id:
				if record.move_id.state == 'posted':
					if record.move_id.force_post:
						record.observations = 'Forzada'
					else:
						record.observations = 'Confirmada'
				else:
					if record.move_id.amount_total == record.total:
						if record.move_id.invoice_date == record.fecha:
							if record.move_id.partner_id.id == record.partner_id_emisor.id or record.move_id.partner_id.id == record.partner_id_receptor.id:
								record.real_state = 'done'
							else:
								record.real_state = 'draft'
								record.observations += ' Cliente/Proveedor.'
						else:
							record.real_state = 'draft'
							record.observations += ' fecha.'
					else:
						record.real_state = 'draft'
						record.observations += ' valor total.'
			if record.real_state == 'draft' and record.state == 'draft' and not record.move_id:
				record.observations = 'No existe factura'
			if record.real_state == 'done' and record.state == 'done' and record.move_id:
				record.observations = 'Coincide'
	
	def unlink(self):
		for record in self:
			if record.move_id:
				record.move_id.attachment_id.unlink()
				record.move_id.cfdi_id = False
				record.move_id.l10n_mx_edi_cfdi_uuid_cusom = False
				record.move_id = False
				record.attachment_id.unlink()
		return super(Cfdi, self).unlink()
	
	#Actualizar el estado del SAT
	def check_status(self):
		# Obtener el primer día del mes actual
		first_date = date.today().replace(day=1)
		# Obtener el último día del mes actual
		last_date = date.today().replace(day=calendar.monthrange(date.today().year, date.today().month)[1])
		
		move_ids = self.env["iia_boveda_fiscal.cfdi"].sudo().search([("fecha", ">=", first_date), ("fecha", "<=", last_date)])
		
		for record in move_ids:
			try:
				status = self.env['account.edi.format']._l10n_mx_edi_get_sat_status(record.partner_id_emisor.vat, record.partner_id_receptor.vat, record.total, record.uuid)
				if status == 'Vigente':
					record.estado_sat = status
				elif status == 'Cancelado':
					record.estado_sat = status
				elif status == 'No Encontrado':
					record.estado_sat = status
			except Exception as e:
				record.message_post(body=_("Failure during update of the SAT status: %(msg)s", msg=str(e)))
	
	#Descarga masiva de XML
	def download_massive_xml_zip(self):
		self = self.with_user(1)
		zip_file = self.env['ir.attachment'].sudo().search([('name', '=', 'XML Masivos.zip')], limit=1)
		if zip_file:
			zip_file.sudo().unlink()
		
		# Funcion para decodificar el archivo
		def isBase64_decodestring(s):
			try:
				decode_archive = base64.decodebytes(s)
				return decode_archive
			except Exception as e:
				raise ValidationError('Error:', + str(e))
		
		tempdirXML = TemporaryDirectory()
		location_tempdir = tempdirXML.name
		# Creando ruta dinamica para poder guardar el archivo zip
		date_act = date.today()
		file_name = 'DescargaMasiva(Fecha de descarga' + " - " + str(date_act) + ")"
		file_name_zip = file_name + ".zip"
		zipfilepath = os.path.join(location_tempdir, file_name_zip)
		path_files = os.path.join(location_tempdir)
		
		# Creando zip
		for xml_file in self.mapped("attachment_id"):
			object_name = xml_file.name
			ruta_ob = object_name
			object_handle = open(os.path.join(location_tempdir, ruta_ob), "wb")
			object_handle.write(isBase64_decodestring(xml_file.datas))
			object_handle.close()
		
		with ZipFile(zipfilepath, 'w') as zip_obj:
			for file in os.listdir(path_files):
				file_path = os.path.join(path_files, file)
				if file_path != zipfilepath:
					zip_obj.write(file_path, basename(file_path))
		
		with open(zipfilepath, 'rb') as file_data:
			bytes_content = file_data.read()
			encoded = base64.b64encode(bytes_content)
		
		data = {
			'name': 'XML Masivos.zip',
			'type': 'binary',
			'datas': encoded,
			'company_id': self.env.company.id
		}
		attachment = self.env['ir.attachment'].sudo().create(data)
		return self.download_zip(file_name_zip, attachment.id)
	
	#Hacer peticion al controlador para descargar el archivo guardado
	def download_zip(self, filename, id_file):
		path = "/web/binary/download_document?"
		model = "ir.attachment"
		
		url = path + "model={}&id={}&filename={}".format(model, id_file, filename)
		return {
			'type': 'ir.actions.act_url',
			'url': url,
			'target': 'self',
		}
	
	#Obtener información del xml general
	def get_cfdi_values(self):
		self = self.with_user(1)
		xml_data = self.get_cfdi_data(self.attachment_id.datas)
		
		cfdi_type = xml_data['Comprobante']['@TipoDeComprobante']
		
		data = {
			'uuid': xml_data['Comprobante']['Complemento']['TimbreFiscalDigital']['@UUID'],
			'supplier_rfc': xml_data['Comprobante']['Emisor']['@Rfc'],
			'supplier_name': xml_data['Comprobante']['Emisor']['@Nombre'],
			'customer_rfc': xml_data['Comprobante']['Receptor']['@Rfc'],
			'customer_name': xml_data['Comprobante']['Receptor']['@Nombre'],
			'amount_total': xml_data['Comprobante']['@Total'],
			'sello': xml_data['Comprobante']['@Sello'] if '@Sello' in xml_data['Comprobante'] else '',
			'sello_sat': xml_data['Comprobante']['Complemento']['TimbreFiscalDigital']['@SelloSAT'],
			'certificate_number': xml_data['Comprobante']['@NoCertificado'],
			'certificate_sat_number': xml_data['Comprobante']['Complemento']['TimbreFiscalDigital']['@NoCertificadoSAT'],
			'expedition': xml_data['Comprobante']['@LugarExpedicion'],
			'fiscal_regime': xml_data['Comprobante']['Emisor']['@RegimenFiscal'],
			'emission_date_str': xml_data['Comprobante']['@Fecha'].replace('T', ' '),
			'stamp_date': xml_data['Comprobante']['Complemento']['TimbreFiscalDigital']['@FechaTimbrado'].replace('T', ' '),
			'concepts': xml_data['Comprobante']['Conceptos']['Concepto']
		}
		
		if cfdi_type in ['P', 'SP']:
			payment_tax_list = []
			payments_list = xml_data['Comprobante']['Complemento']['pago20:Pagos']['pago20:Pago']
			payments_list = self.get_data_iterable(payments_list)
			if payments_list:
				for payment_list in payments_list:
					payment_date = payment_list["@FechaPago"][:10],
					payments = payment_list["pago20:DoctoRelacionado"]
					payments = self.get_data_iterable(payments)
					
					if payments:
						for payment in payments:
							if payment.get("@ObjetoImpDR") and payment.get("@ObjetoImpDR") == '02':
								payment_taxes = payment["pago20:ImpuestosDR"]["pago20:TrasladosDR"]["pago20:TrasladoDR"]
								payment_taxes = self.get_data_iterable(payment_taxes)
								
								if payment_taxes:
									for payment_tax in payment_taxes:
										payment_tax_data = {
											"name": payment["@IdDocumento"],
											"serie": payment.get("@Serie"),
											"folio": payment.get("@Folio"),
											"currency": payment["@MonedaDR"],
											"currency_rate": payment["@EquivalenciaDR"],
											"paid_amount": payment["@ImpPagado"],
											"previous_balance": payment["@ImpSaldoAnt"],
											"current_balance": payment["@ImpSaldoInsoluto"],
											"subject_tax": payment["@ObjetoImpDR"],
											"payment_date": payment_date[0],
											"cfdi_id": self.id,
											"tax_amount": payment_tax.get("@ImporteDR"),
											"base_amount": payment_tax["@BaseDR"],
											"type_tax": payment_tax["@ImpuestoDR"],
											"base_tax": float(payment_tax["@TasaOCuotaDR"]) * 100 if payment_tax.get("@TasaOCuotaDR") else 0,
											"exempt_tax": True if payment_tax.get("@TipoFactorDR") == 'Exento' else False,
										}
										payment_tax_list.append(payment_tax_data)
						data["payment_taxes"] = payment_tax_list
		return data
	
	#Obtener la información de las lineas del xml dependiendo del tipo
	def get_data_iterable(self, data):
		if type(data) is list:
			data = data
		elif type(data) is OrderedDict:
			data = data.items()
		else:
			data = [data]
		return data
	
	# Recalcula impuestos que no se hayan agregado al importar el XML por falta de configuración
	def set_concept_tax_ids(self):
		self = self.with_user(1)
		for rec in self:
			for tax_line in rec.tax_ids.filtered(lambda tax: not tax.tax_id):
				cfdi_type = tax_line.iia_boveda_fiscal_cfdi_id.tipo_de_comprobante
				t_id = False
				amount = round(tax_line.tasa_cuota * 100, 2) if tax_line.tax_type == 'traslado' else round(-(tax_line.tasa_cuota * 100), 2)
				tax_domain = [('amount', '=', amount), ('company_id', '=', rec.company_id.id)]
				if tax_line.impuesto == '002':
					tax_domain.append(("l10n_mx_tax_type", "=", "iva"))
				elif tax_line.impuesto == '003':
					tax_domain.append(("l10n_mx_tax_type", "=", "ieps"))
				elif tax_line.impuesto == '001':
					tax_domain.append(("l10n_mx_tax_type", "=", "isr"))
				if cfdi_type in ['I', 'E']:
					tax_domain.append(('type_tax_use', '=', 'sale'))
					t_id = self.env['account.tax'].sudo().search(tax_domain, limit=1)
				if cfdi_type in ['SI', 'SE']:
					tax_domain.append(('type_tax_use', '=', 'purchase'))
					t_id = self.env['account.tax'].sudo().search(tax_domain, limit=1)
				if t_id:
					tax_line.sudo().write({'tax_id': t_id.id})
	
	def set_journal_id(self):
		self = self.with_user(1)
		for rec in self:
			journal_id = self.env["account.journal"].sudo().search([("company_id.id", "=", rec.company_id.id), ("tipo_de_comprobante_boveda", "=", rec.tipo_de_comprobante)], limit=1)
			
			if journal_id and not rec.journal_id:
				rec.write({
					"journal_id": journal_id.id
				})
	
	#Asignar contactos si es que faltan
	def set_partner_cfdi(self):
		self = self.with_user(1)
		for rec in self:
			xml_data = self.get_cfdi_data(self.attachment_id.datas)
			emitter_partner_id, recipient_partner_id = self.get_cfdi_partners(xml_data)
			rec.write({
				"partner_id_emisor": emitter_partner_id.id if emitter_partner_id else False,
				"partner_id_receptor": recipient_partner_id.id if recipient_partner_id else False
			})
	
	#Crear los impuestos pagados
	def create_payment_tax(self):
		for rec in self:
			if rec.tipo_de_comprobante in ['P', 'SP']:
				if rec.tax_paymnent_ids:
					rec.tax_paymnent_ids.unlink()
				cfdi_values = rec.get_cfdi_values()
				rec.set_partner_cfdi()
				payment_taxes = cfdi_values.get("payment_taxes")
				if payment_taxes:
					self.env["account.cfdi.payment.tax"].sudo().create(payment_taxes)
	
	
	# Recalcular cfdi y factura por si hay algun fallo en la lectura del xml
	def recalculate_cfdi_invoice(self):
		for rec in self:
			cfdi_values = rec.get_cfdi_values()
			concepts = cfdi_values.get('concepts')
			lines = self.get_data_iterable(concepts)
			initial_sequence = len(rec.concepto_ids)
			
			for line_value in lines:
				line = self.get_data_iterable(line_value)
				line_id = rec.create_concept_line(line[0], initial_sequence)
				if line_id:
					rec.set_product_line(line, line_id)
					rec.set_tax_line(line, line_id)
				else:
					rec.update_type_tax(line[0])
			
			rec.set_concept_tax_ids()
			
			if rec.tax_ids.filtered(lambda line: not line.tax_id):
				raise ValidationError(f"Es necesario colocar todos los impuestos para poder seguir, favor de revisar.")
			
			if rec.move_id:
				rec.move_id.button_draft()
				rec.move_id.invoice_line_ids.unlink()
				rec.create_move_line_invoice()
				rec.move_id._compute_amount()
				rec.move_id.write({
					'state': 'posted',
				})
	
	#Crear linea de concepto por si no se creo al leer el xml
	def create_concept_line(self, line, initial_sequence):
		if line and not self.concepto_ids.filtered(lambda li: li.cantidad == float(line.get("@Cantidad")) and li.clave_prod_serv == line.get("@ClaveProdServ") and li.descripcion == line.get("@Descripcion")):
			initial_sequence += 1
			
			uom_id = False
			uom_unspsc_id = self.env['product.unspsc.code'].sudo().search([('code', '=', str(line['@ClaveUnidad']))], limit=1)
			if uom_unspsc_id:
				uom_id = self.env['uom.uom'].sudo().search([('unspsc_code_id.id', '=', uom_unspsc_id.id)], limit=1)
			unspsc_product_category_id = self.env['product.unspsc.code'].sudo().search([('code', '=', str(line['@ClaveProdServ']))], limit=1)
			
			data = {
				'sequence': initial_sequence,
				'code_cfdi': self.code,
				'fecha': self.fecha,
				'folio': self.folio,
				'forma_pago': self.forma_pago,
				'lugar_expedicion': self.lugar_expedicion,
				'metodo_pago': self.metodo_pago,
				'moneda': self.moneda,
				'no_certificado': self.no_certificado,
				'sello': self.sello,
				'serie': self.serie,
				'subtotal': self.subtotal,
				'tipo_de_comprobante': self.tipo_de_comprobante,
				'total': self.total,
				'version': self.version,
				'partner_id_emisor': self.partner_id_emisor.id if self.partner_id_emisor else False,
				'partner_id_receptor': self.partner_id_receptor.id if self.partner_id_receptor else False,
				'clave_prod_serv': line['@ClaveProdServ'] if '@ClaveProdServ' in line else '',
				'no_identificacion': line['@NoIdentificacion'] if '@NoIdentificacion' in line else '',
				'cantidad': float(line['@Cantidad']),
				'clave_unidad': line['@ClaveUnidad'] if '@ClaveUnidad' in line else '',
				'unidad': line['@Unidad'] if '@Unidad' in line else '',
				'descripcion': line['@Descripcion'],
				'descuento': float(line['@Descuento']) if '@Descuento' in line else 0,
				'valor_unitario': float(line['@ValorUnitario']),
				'uom_id': uom_id.id if uom_id else uom_id,
				'unspsc_product_category_id': unspsc_product_category_id.id if unspsc_product_category_id else False,
				'importe': float(line['@Importe']),
				'iia_boveda_fiscal_cfdi_id': self.id,
			}
			line_id = self.concepto_ids.sudo().create(data)
			return line_id
		return False
	
	#Asignar impuestos faltantes al recalcular
	def set_tax_line(self, line, line_id):
		cfdi_line = self.get_cfdi_tax_lines({},line, self.tipo_de_comprobante, self.partner_id_receptor)
		if cfdi_line and cfdi_line.get("tax_ids"):
			line_id.tax_ids = cfdi_line["tax_ids"]
	
	#Asignar producto a la linea al recalcular
	def set_product_line(self, line, line_id):
		data_line = self.search_cfdi_product(line, self.tipo_de_comprobante, {}, self.partner_id_emisor, self.partner_id_receptor)
		if data_line.get("product_tmpl_id"):
			line_id.write({"product_tmpl_id": data_line.get("product_tmpl_id")})
		if data_line.get("account_id"):
			line_id.write({"account_id": data_line.get("account_id")})
	
	#Crear linea contable al recalcular el cfdi
	def create_move_line_invoice(self):
		i = 1
		for linea in self.concepto_ids:
			if float(linea.importe) > 0:
				tax_ids = []
				for impuesto in linea.tax_ids:
					tax_ids.append(impuesto.tax_id.id)
				
				if linea.account_id:
					linea_account_id = linea.account_id.id
				else:
					linea_account_id = self.account_id.id
				
				tax_test = tax_ids
				tax_ids = []
				for tax in tax_test:
					if tax != False:
						tax_ids.append(tax)
				
				line_id = self.env['account.move.line'].with_context(check_move_validity=False).sudo().create({
					'move_id': self.move_id.id,
					'sequence': i,
					'name': linea.descripcion,
					'quantity': float(linea.cantidad),
					'product_uom_id': linea.uom_id.id,
					'discount': (float(linea.descuento) * 100) / float(linea.importe),
					'price_unit': float(linea.valor_unitario),
					'tax_ids': [(6, 0, tax_ids)],
					'account_id': linea_account_id,
					'analytic_distribution': self.analytic_distribution,
					'partner_id': self.move_id.partner_id.id,
				})
				
				if linea.product_tmpl_id:
					product_id = self.env['product.product'].sudo().search(
						[('product_tmpl_id', '=', linea.product_tmpl_id.id)])
					line_id.write({
						'product_id': product_id.id,
					})
				line_id.write({
					'discount': (float(linea.descuento) * 100) / float(linea.importe),
					'price_unit': float(linea.valor_unitario)
				})
				i = i + 1
	
	#Actualizar las lineas del concepto para adicionar los impuestos restantes
	def update_type_tax(self, line):
		line_id = self.concepto_ids.filtered(lambda li: li.cantidad == float(line.get("@Cantidad")) and li.clave_prod_serv == line.get("@ClaveProdServ") and li.descripcion == line.get("@Descripcion"))
		if line and line_id:
			line_id.tax_ids.unlink()
			self.set_tax_line(line, line_id)
	
	def set_move_id(self):
		self = self.with_user(1)
		for rec in self:
			move_id = self.env["account.move"]
			if rec.tipo_de_comprobante in ["I", "E"]:
				move_id = move_id.search([("move_type", "in", ["out_invoice", "out_refund"]), ("l10n_mx_edi_cfdi_uuid", "=", rec.uuid), ("state", "=", "posted"), ("cfdi_id", "=", False)], limit=1)
			elif rec.tipo_de_comprobante in ["SI", "SE"]:
				folio = rec.folio
				move_id = self.env['account.move'].search([('partner_id', '=', rec.partner_id_emisor.id), ('ref', 'ilike', folio),
					 ('move_type', 'in', ['in_invoice', 'in_refund']), ("cfdi_id", "=", False),
					 ("state", "=", "posted"), ("cfdi_id", "=", False)], limit=1)
				if not move_id:
					if rec.serie:
						folio = rec.serie + folio
						move_id = self.env['account.move'].search(
							[('partner_id', '=', rec.partner_id_emisor.id), ('ref', '=', folio),
							 ('move_type', 'in', ['in_invoice', 'in_refund']), ("cfdi_id", "=", False),
							 ("state", "=", "posted")], limit=1)
					if not move_id:
						min_amount = rec.subtotal - 1
						max_amount = rec.subtotal + 1
						invoice_date = rec.fecha
						move_id = self.env['account.move'].sudo().search(
							[('partner_id', '=', rec.partner_id_emisor.id), ('move_type', 'in', ['in_invoice']),
							 ("cfdi_id", "=", False), ("state", "=", "posted"), ("amount_untaxed", ">=", min_amount),("amount_untaxed", "<=", max_amount),
							 ("invoice_date", "=", invoice_date)], limit=1)
			if move_id:
				rec.write({
					"move_id": move_id.id,
					"state": "done"
				})
				rec.move_id.write({
					"cfdi_id": rec.id
				})