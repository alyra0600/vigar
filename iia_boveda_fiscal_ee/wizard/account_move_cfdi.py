# -*- coding: utf-8 -*-
from odoo import models,fields,api
from odoo.exceptions import RedirectWarning, ValidationError
from odoo.tools import (float_compare)
import logging

_logger = logging.getLogger(__name__)

class LinkMoveCfdi(models.TransientModel):
	_name = 'iia.wizard_account_move_cfdi'
	_description = 'Enlazar factura con CFDI'
	
	company_id = fields.Many2one(comodel_name='res.company', string='Empresa', default=lambda self: self.env.company, readonly=True)
	move_id = fields.Many2one(comodel_name='account.move', string='Factura', required=True)
	currency_id = fields.Many2one(comodel_name='res.currency', string='Moneda', related='move_id.currency_id')
	partner_id = fields.Many2one(comodel_name='res.partner', string=u'Empresa', related='move_id.partner_id')
	amount_total_signed = fields.Monetary(string='Total', related='move_id.amount_total_signed', currency_field='currency_id')
	cfdi_id = fields.Many2one(comodel_name='iia_boveda_fiscal.cfdi', string='CFDI')
	uuid = fields.Char(string='UUID', related='cfdi_id.uuid')
	moneda = fields.Char(string='Moneda', related='cfdi_id.moneda')
	total = fields.Float(string='Total', related='cfdi_id.total')
	partner_id_emisor = fields.Many2one(comodel_name='res.partner', string='Emisor', related='cfdi_id.partner_id_emisor')
	partner_id_receptor = fields.Many2one(comodel_name='res.partner', string='Receptor', related='cfdi_id.partner_id_receptor')
	elementos_cfdi_ids = fields.Many2many('iia_boveda_fiscal.cfdi', string='Lista de asociaciones')
	force_link = fields.Boolean(string='Forzar enlace', default=False)

	@api.onchange('move_id')
	def _onchange_move_id(self):
		if self.move_id and self.move_id.state in ["draft","posted"]:
			elementos_ids = False
			if self.move_id.move_type in ['in_invoice', 'in_refund', 'in_receipt']:
				elementos_ids = self.env['iia_boveda_fiscal.cfdi'].search([('partner_id_emisor', '=', self.move_id.partner_id.id), ('tipo_de_comprobante', 'in', ['SI', 'SE', 'ST', 'SP']),	('move_id','=',False)])
			elif self.move_id.move_type in ['out_invoice', 'out_refund', 'out_receipt']:
				elementos_ids = self.env['iia_boveda_fiscal.cfdi'].search([('move_id','=',False),('partner_id_receptor', '=', self.move_id.partner_id.id), ('tipo_de_comprobante', 'in', ['I', 'E', 'T', 'P'])])
			if elementos_ids:
				self.elementos_cfdi_ids = elementos_ids.ids
				self.search_possible_cfdi_id(elementos_ids)
		else:
			raise ValidationError("Es nesecario seleccionar una factura y que está se encuentre en un estado diferente de cancelado.")
		
	def search_possible_cfdi_id(self, cfdi_ids):
		cfdi_ids = cfdi_ids.filtered(lambda cfdi: cfdi.subtotal == self.move_id.amount_untaxed or cfdi.fecha == self.move_id.invoice_date)
		if cfdi_ids:
			self.cfdi_id = cfdi_ids[0].id
	
	#Procesar los CFDIs
	def process(self):
		self = self.with_user(1)
		for record in self:
			record = record.with_context(skip_invoice_sync=True, check_move_validity=False)
			if record.cfdi_id:
				if not record.move_id.l10n_mx_edi_cfdi_uuid_cusom:
					if float_compare(abs(record.total), abs(record.move_id.amount_total_in_currency_signed), precision_digits=record.currency_id.rounding) == 0 or self.force_link:
						record.move_id.with_context(skip_invoice_sync=True, check_move_validity=False).write({
							"cfdi_id": record.cfdi_id.id,
							"attachment_id": record.cfdi_id.attachment_id.id,
							"l10n_mx_edi_cfdi_uuid_cusom": record.cfdi_id.uuid,
							"invoice_date": record.cfdi_id.fecha
						})
						if record.move_id.move_type == 'out_invoice':
							if record.cfdi_id.attachment_id:
								if not record.move_id.l10n_mx_edi_document_ids:
									create_edi = self.env['l10n_mx_edi.document'].create({
										'attachment_id': record.cfdi_id.attachment_id.id,
										'invoice_ids': record.move_id.ids,
										'move_id': record.move_id.id,
										'state': 'invoice_sent',
										'datetime': record.move_id.create_date
									})
									record.move_id.with_context(skip_invoice_sync=True, check_move_validity=False).write({
										'l10n_mx_edi_document_ids': [(6, False, [create_edi.id])],
										'l10n_mx_edi_cfdi_uuid': record.move_id.l10n_mx_edi_cfdi_uuid_cusom,
										'state': 'posted'
									})
								elif record.move_id.l10n_mx_edi_document_ids:
									data = {
										'move_id': record.move_id.id,
										'invoice_ids': record.move_id.ids,
										'attachment_id': record.cfdi_id.attachment_id.id,
										'state': 'invoice_sent',
										'datetime': record.move_id.create_date
									}
									self.env["l10n_mx_edi.document"].sudo().create([data])
									record.move_id.with_context(skip_invoice_sync=True, check_move_validity=False).write({'l10n_mx_edi_cfdi_uuid': record.move_id.l10n_mx_edi_cfdi_uuid_cusom, 'state': 'posted'})
						if record.cfdi_id.attachment_id:
							record.cfdi_id.attachment_id.sudo().with_context(skip_invoice_sync=True, check_move_validity=False).write({
								'res_model': 'account.move',
								'res_id': record.move_id.id
							})
						folio = f"{record.cfdi_id.serie}-{record.cfdi_id.folio}" if record.cfdi_id.serie and record.cfdi_id.folio else f"{record.cfdi_id.serie}" if record.cfdi_id.serie and not record.cfdi_id.folio else f"{record.cfdi_id.folio}" if not record.cfdi_id.serie and record.cfdi_id.folio else ''
						record.move_id.sudo().with_context(skip_invoice_sync=True, check_move_validity=False).write({
							'ref': folio
						})
						record.cfdi_id.sudo().with_context(skip_invoice_sync=True, check_move_validity=False).write({
							'move_id': record.move_id.id,
							'state': 'done',
							'observations': ''
						})
					else:
						raise ValidationError('El valor no coincide.')
				else:
					raise ValidationError('El documento ya tiene asignado un UUID.')
			else:
				raise ValidationError('Debe ingresar un CFDI.')

