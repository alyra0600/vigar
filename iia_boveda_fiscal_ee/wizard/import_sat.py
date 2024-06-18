# -*- coding: utf-8 -*-
from odoo import models,fields,api
import logging

_logger = logging.getLogger(__name__)

class ImportXML(models.TransientModel):
	_name ='iia.import.sat'
	_description = 'Importación CFDI desde el SAT'
	
	date_from = fields.Date(string='Desde', default=fields.Date.today())
	date_to = fields.Date(string='Hasta', default=fields.Date.today())
	type = fields.Selection(selection=[('0','Todo'),('1','Emitidas'),('2','Recibidas')], string='Tipo',	default= '0')
	company_id = fields.Many2one(comodel_name='res.company', string='Empresa', default=lambda self: self.env.company, readonly=True)

	def import_sat(self):
		response = False
		if self.type == '0':
			response = self.company_id.download_cfdi_invoices_sat(self.date_from, self.date_to)
		elif self.type == '1':
			response = self.company_id.download_cfdi_invoices_sat(self.date_from, self.date_to, "customer")
		elif self.type == '2':
			response = self.company_id.download_cfdi_invoices_sat(self.date_from, self.date_to, "supplier")
		return response