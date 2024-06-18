# -*- coding: utf-8 -*-
from odoo import models,fields,api, _
from odoo.exceptions import RedirectWarning, ValidationError, UserError
from odoo.tools import (
    float_compare
)

import logging

_logger = logging.getLogger(__name__)


class CfdiAccountMoveLink(models.TransientModel):
	_name = 'iia.wizard_cfdi_account_move_link'
	_description = 'Enlazar CFDI con Factura'
	
	elementos_ids = fields.Many2many('account.move', string='Lista de asociaciones')
	active_id = fields.Many2one('iia_boveda_fiscal.cfdi', default='_get_cfdi_active')
	invoice_id = fields.Many2one('account.move', string='Factura a asociar')
	force_link = fields.Boolean(string='Force Link', default=False)

	def _get_cfdi_active(self):
		self = self.with_context(cfdi_link=True)
		if self.env.context and self.env.context.get('active_ids'):
			return self.env.context.get('active_ids')
		return []

	@api.onchange('active_id')
	def _onchange_active_ids(self):
		self = self.with_context(cfdi_link=True)
		active_ids = self.env.context.get('active_ids')
		if len(active_ids) == 1:
			elementos_ids = False
			for id_active in active_ids:
				cfdi = self.env['iia_boveda_fiscal.cfdi'].search([('id', '=', id_active)])
				if cfdi and cfdi.state == 'draft' and not cfdi.move_id:
					if cfdi.tipo_de_comprobante in ['SI', 'SE', 'ST', 'SP']:
						elementos_ids = self.env['account.move'].search([('l10n_mx_edi_cfdi_uuid_cusom','=',False),('partner_id', '=', cfdi.partner_id_emisor.id), ('move_type', 'in', ['in_invoice', 'in_refund', 'in_receipt']),("state","in",["posted","draft"])])
					elif cfdi.tipo_de_comprobante in ['I', 'E', 'T', 'P']:
						elementos_ids = self.env['account.move'].search([('l10n_mx_edi_cfdi_uuid_cusom','=',False),	('partner_id', '=', cfdi.partner_id_receptor.id), ('move_type', 'in', ['out_invoice', 'out_refund', 'out_receipt']),("state","in",["posted","draft"])])
					if elementos_ids:
						self.elementos_ids = elementos_ids.ids
						self.search_possible_cfdi_id(elementos_ids, cfdi)
				else:
					raise ValidationError("Es necesario seleccionar un elemento que no tenga asignado una factura y se encuentre en estado borrado, favor de validar.")
		else:
			raise UserError(_('Solo puede procesar un elemento a la vez para esta opcion'))
		
	#Busca una posible factura con ciertas coincidencias como el total, el emisor y la fecha
	def search_possible_cfdi_id(self, invoice_ids, cfdi_id):
		invoice_ids = invoice_ids.filtered(lambda invoice: cfdi_id.subtotal == invoice.amount_untaxed or cfdi_id.fecha == invoice.invoice_date)
		if invoice_ids:
			self.invoice_id = invoice_ids[0].id

	#Procesar los cfdis con las facturas
	def process(self):
		active_ids = self.env.context.get('active_ids')
		if self.force_link:
			for id_active in active_ids:
				cfdi = self.env['iia_boveda_fiscal.cfdi'].search([('id', '=', id_active)])
				if self.invoice_id.move_type == 'out_invoice':
					self.set_edi_document_invoice(cfdi)
				cfdi.sudo().write({
					"move_id": self.invoice_id.id,
					"state": "done"
				})
				cfdi.move_id.sudo().write({
					"cfdi_id": cfdi.id,
					"attachment_id": cfdi.attachment_id.id
				})
		else:
			for id_active in active_ids:
				cfdi = self.env['iia_boveda_fiscal.cfdi'].search([('id', '=', id_active)])
				if self.invoice_id.amount_total != cfdi.total or self.invoice_id.date != cfdi.fecha:
					raise UserError(_('Revise las Notas del CFDI especifico, hay datos no coincidentes que no permiten Enlazar la factura'))
				else:
					self.set_edi_document_invoice(cfdi)
					cfdi.sudo().write({
						"move_id": self.invoice_id.id,
						"state": "done"
					})
					cfdi.move_id.sudo().write({
						"cfdi_id": cfdi.id,
						"attachment_id": cfdi.attachment_id.id
					})
					
	def set_edi_document_invoice(self, cfdi):
		if cfdi.attachment_id:
			if not self.invoice_id.l10n_mx_edi_document_ids:
				create_edi = self.env['l10n_mx_edi.document'].create({
					'attachment_id': cfdi.attachment_id.id,
					'invoice_ids': self.invoice_id.ids,
					'move_id': self.invoice_id.id,
					'state': 'invoice_sent',
					'datetime': self.invoice_id.create_date
				})
				self.invoice_id.write({
					'l10n_mx_edi_document_ids': [(6, False, [create_edi.id])],
					'l10n_mx_edi_cfdi_uuid': self.invoice_id.l10n_mx_edi_cfdi_uuid_cusom,
					'state': 'posted'
				})
			elif self.invoice_id.l10n_mx_edi_document_ids:
				data = {
					'move_id': self.invoice_id.id,
					'invoice_ids': self.invoice_id.ids,
					'attachment_id': cfdi.attachment_id.id,
					'state': 'invoice_sent',
					'datetime': self.invoice_id.create_date
				}
				self.env["l10n_mx_edi.document"].sudo().create([data])
				self.invoice_id.write({'l10n_mx_edi_cfdi_uuid': self.invoice_id.l10n_mx_edi_cfdi_uuid_cusom, 'state': 'posted'})