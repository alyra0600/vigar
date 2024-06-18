# -*- coding: utf-8 -*-
from odoo import models,fields,api,_
from odoo.exceptions import RedirectWarning, ValidationError, UserError
import logging

_logger = logging.getLogger(__name__)

class CheckSatStatusCfdi(models.TransientModel):
	_name = 'iia.wizard_check_sat_status_cfdi'
	_description = 'Chequear Estado CFDI'

	def _get_active_ids(self):
		x = []
		if self.env.context and self.env.context.get('active_ids'):
			x = self.env.context.get('active_ids')
		self.elementos_cfdi_ids = self.env['iia_boveda_fiscal.cfdi'].browse(x)

	elementos_cfdi_ids = fields.Many2many('iia_boveda_fiscal.cfdi', compute=_get_active_ids, string='Lista CFDI')

	def check_status(self):
		if len(self.elementos_cfdi_ids) > 0:
			for record in self.elementos_cfdi_ids:
				try:
					status = self.env['account.edi.format']._l10n_mx_edi_get_sat_status(record.partner_id_emisor.vat,
																						record.partner_id_receptor.vat,
																						record.total, record.uuid)
				except Exception as e:
					record.message_post(body=_("Failure during update of the SAT status: %(msg)s", msg=str(e)))
					continue

				if status == 'Vigente':
					record.estado_sat = status
				elif status == 'Cancelado':
					record.estado_sat = status
				elif status == 'No Encontrado':
					record.estado_sat = status
				else:
					continue
		else:
			raise UserError(_('Debe seleccionar algunos CFDI para comprobar Estado en el SAT'))

