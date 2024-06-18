# -*- coding: utf-8 -*-
from odoo import models,fields,api,_
from odoo.exceptions import RedirectWarning, ValidationError, UserError
from odoo.tools import (
    float_compare
)

import logging

_logger = logging.getLogger(__name__)


class ProcessMultiCfdi(models.TransientModel):
	_name = 'iia.wizard_process_multi_cfdi'
	_description = 'Multiprocesamiento CFDI'

	def _get_active_ids(self):
		x = []
		if self.env.context and self.env.context.get('active_ids'):
			x = self.env.context.get('active_ids')
		self.elementos_cfdi_ids = self.env['iia_boveda_fiscal.cfdi'].browse(x)

	elementos_cfdi_ids = fields.Many2many('iia_boveda_fiscal.cfdi', compute=_get_active_ids, string='Lista CFDI')

	def process_multi_cfdi(self):
		if len(self.elementos_cfdi_ids) > 0:
			for record in self.elementos_cfdi_ids:
				record.action_done()
		else:
			raise UserError(_('Debe seleccionar algunos CFDI para Procesar'))

