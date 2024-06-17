# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError

class AccountMove(models.Model):
	_inherit = 'account.move'
	
	@api.model
	def _get_cfdi_id(self):
		for record in self:
			record.cfdi_id = self.env['iia_boveda_fiscal.cfdi'].search([('move_id', '=', record.id)], limit=1)
	
	cfdi_id = fields.Many2one(comodel_name='iia_boveda_fiscal.cfdi', compute='_get_cfdi_id', string='CFDI', store=True, index=True)
	attachment_id = fields.Many2one("ir.attachment", 'Attachment', compute='_compute_attachment_id', store=True)
	l10n_mx_edi_cfdi_uuid_cusom = fields.Char(string='Fiscal Folio UUID', copy=False, readonly=True, compute='_compute_cfdi_uuid', store=True)
	hide_message = fields.Boolean(string='Hide Message', default=False, copy=False)
	total_analysis_cfdi = fields.Float(compute="_compute_total_analysis_cfdi", string='Analysis CFDI', store=True)
	force_post = fields.Boolean(string='Forzar Confirmación', default=False)
	code_invoice_prepaid = fields.Char(string="Codigo de prepago")
	
	def name_get(self):
		if not self.env.context.get("cfdi_link"):
			return super().name_get()
		else:
			result = []
			for record in self:
				name = f"{record.name} ({record.ref if record.ref else ''}) - ${round(record.amount_total,2)}"
				result.append((record.id, name))
			return result

	@api.depends('cfdi_id','amount_total')
	def _compute_total_analysis_cfdi(self):
		for move in self:
			move_diff = 0.0
			if move.cfdi_id:
				if move.amount_total > move.cfdi_id.total:
					move_diff = move.amount_total - move.cfdi_id.total
				else:
					move_diff = move.cfdi_id.total - move.amount_total
				move.l10n_mx_edi_cfdi_uuid_cusom = move.cfdi_id.uuid
			move.total_analysis_cfdi = move_diff

	@api.depends('cfdi_id')
	def _compute_attachment_id(self):
		for record in self:
			if record.cfdi_id:
				record.attachment_id = record.cfdi_id.attachment_id

	@api.depends("cfdi_id","state")
	def _compute_cfdi_uuid(self):
		for inv in self:
			if inv.state != 'cancel':
				inv_cfdi = self.env['iia_boveda_fiscal.cfdi'].search([('move_id', '=', inv.id)])
				if len(inv_cfdi) == 1:
					inv.l10n_mx_edi_cfdi_uuid_cusom = inv_cfdi.uuid
				else:
					inv.l10n_mx_edi_cfdi_uuid_cusom = False
	
	#Abrir el CFDI con el cual está ligado
	def action_view_source_cfdi(self):
		self.ensure_one()
		source_orders = self.cfdi_id
		result = self.env['ir.actions.act_window']._for_xml_id('iia_boveda_fiscal_ee.action_boveda_fiscal_cfdi')
		if len(source_orders) > 1:
			result['domain'] = [('id', 'in', source_orders.ids)]
		elif len(source_orders) == 1:
			result['views'] = [(self.env.ref('iia_boveda_fiscal_ee.view_iia_boveda_fiscal_cfdi_form', False).id, 'form')]
			result['res_id'] = source_orders.id
		else:
			result = {'type': 'ir.actions.act_window_close'}
		return result

	#Adición de validaciones al momento de confirmar una factura proveedor
	def action_post(self):
		# Validacion si el proveedor necesita uuid para poder confirmar y si la factura no cuenta con el
		if self.move_type == "in_invoice" and self.partner_id and self.partner_id.x_is_uuid_required and not self.l10n_mx_edi_cfdi_uuid_cusom:
			raise UserError(_("No puede confirmar la factura ya que el proveedor requiere que se cuente con UUID de la factura, favor de verificar."))
		if self.move_type not in ['in_invoice']:
			if self.cfdi_id and self.force_post:
				self.cfdi_id.observations = 'Forzada'
				return super(AccountMove, self).action_post()
			elif self.cfdi_id:
				if self.cfdi_id.total != self.amount_total:
					if self.cfdi_id.fecha != self.date:
						if self.move_type in ['in_invoice', 'in_refund', 'in_receipt']:
							if self.cfdi_id.partner_id_emisor.id != self.partner_id.id:
								raise UserError(_('No puede confirmar la factura, los datos generales de FECHA, EMISOR y TOTAL no coinciden con el CFDI asignado'))
						elif self.move_type in ['out_invoice', 'out_refund', 'out_receipt']:
							if self.cfdi_id.partner_id_receptor.id != self.partner_id.id:
								raise UserError(_('No puede confirmar la factura, los datos generales de FECHA, RECEPTOR y TOTAL no coinciden con el CFDI asignado'))
						raise UserError(_('No puede confirmar la factura, los datos generales de FECHA y TOTAL no coinciden con el CFDI asignado'))
					raise UserError(_('No puede confirmar la factura, los datos generales respecto al TOTAL no coinciden con el CFDI asignado'))
				else:
					self.cfdi_id.observations = 'Valores coincidentes'
					return super(AccountMove, self).action_post()
			elif self.move_type in ['in_invoice'] and not self.cfdi_id:
				raise UserError(_('No puede confirmar una factura de Proveedor sin CFDI asociado'))
			else:
				return super(AccountMove, self).action_post()
		else:
			#Asignar el nombre de la serie y folio si es que tiene
			if self.cfdi_id and self.move_type == 'out_invoice':
				folio = f"{self.cfdi_id.serie}-{self.cfdi_id.folio}" if self.cfdi_id.serie and self.cfdi_id.folio else f"{self.cfdi_id.serie}" if self.cfdi_id.serie and not self.cfdi_id.folio else f"{self.cfdi_id.folio}" if not self.cfdi_id.serie and self.cfdi_id.folio else ''
				if folio != '' and not self.env["account.move"].search([("name","=",folio),("state","=","posted")],limit=1):
					self.name = folio
			return super(AccountMove, self).action_post()

	#Adicion de funciones al momento de cancelar una factura con CFDI
	def button_cancel(self):
		for rec in self:
			if rec.cfdi_id:
				rec.attachment_id.write({
					'res_model': 'iia_boveda_fiscal.cfdi',
					'res_id': rec.cfdi_id.id,
				})
				rec.cfdi_id.write({
					"state": "draft",
					"move_id": False
				})
				rec.write({
					'auto_post': 'no',
					'state': 'cancel',
					'cfdi_id': False,
					'l10n_mx_edi_cfdi_uuid_cusom': False
				})
				if rec.l10n_mx_edi_document_ids:
					rec.l10n_mx_edi_document_ids.unlink()
			else:
				res = super().button_cancel()
				return res