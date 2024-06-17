# -*- coding: utf-8 -*-
from odoo import models,fields,api
from odoo.exceptions import RedirectWarning, ValidationError
from zipfile import ZipFile

import base64
import tempfile
import os
import logging

_logger = logging.getLogger(__name__)

class ImportXML(models.TransientModel):
	_name ='iia.import.zip'
	_description = 'Importacion con archivo ZIP'
	
	file = fields.Binary(string='Archivo',required=True)
	file_name = fields.Char(string='Nombre del archivo',required=True)
	company_id = fields.Many2one(comodel_name='res.company', string='Compañía',	default=lambda self: self.env.company,readonly=True)
	result = fields.Char(string=u'Resultado')
	state = fields.Selection(selection=[('draft', 'Seleccionar'),('done', 'Importado'),],string='Estado',default='draft')

	def import_zip(self):
		count_xml = 0
		if self.file:
			zip_file_id = self.env['ir.attachment'].create({
				'name': self.file_name,
				'type': 'binary',
				'company_id': self.company_id.id,
				'datas': self.file,
				'store_fname': self.file_name,
				'mimetype': 'application/zip'
			})
			fd, path = tempfile.mkstemp()
			with os.fdopen(fd, 'wb') as tmp:
				tmp.write(base64.b64decode(zip_file_id.datas))

			try:
				with ZipFile(path,'r') as zip:
					attachment_list = []
					for filename in zip.namelist():
						with zip.open(filename) as file:
							xml_content = file.read()
							attachment_data = {
								'name': filename,
								'type': 'binary',
								'company_id': self.company_id.id,
								'datas': base64.b64encode(xml_content),
								'store_fname': filename,
								'mimetype': 'application/xml'
							}
							attachment_list.append(attachment_data)
					if attachment_list:
						cfdi_ids = self.env['iia_boveda_fiscal.cfdi'].create_cfdis(attachment_list)
						count_xml = len(cfdi_ids)
			except Exception as e:
				raise ValidationError(e)

		self.write({
			'result': "Archivos XML procesados correctamente: " + str(count_xml),
			'state': 'done',
		})
			
		return {
            'type': 'ir.actions.act_window',
            'res_model': 'iia.import.zip',
            'view_mode': 'form',
            'view_type': 'form',
            'res_id': self.id,
            'views': [(False, 'form')],
            'target': 'new',
        }
