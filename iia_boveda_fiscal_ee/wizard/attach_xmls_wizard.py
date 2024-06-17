# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
import logging
_logger = logging.getLogger(__name__)

TYPE_CFDI22_TO_CFDI33 = {
    'ingreso': 'I',
    'egreso': 'E',
    'traslado': 'T',
    'nomina': 'N',
    'pago': 'P',
}

class AttachXmlsWizard(models.TransientModel):
    _name = 'multi.file.attach.xmls.wizard'
    _description = 'Importación por multiples XML'
    
    company_id = fields.Many2one(comodel_name='res.company', string='Compañía', default=lambda self: self.env.company, readonly=True)
    filedata_file = fields.Many2many('ir.attachment', 'class_ir_attachments_rel', 'class_id', 'attachment_id', 'Archivos XML')
    filedata_name = fields.Char(string="Nombre de archivo")

    def import_file(self):
            if len(self.filedata_file) > 0:
                attachment_list = []
                for content in self.filedata_file:
                    try:
                        attachment_data = {
                            'name': content.name,
                            'type': 'binary',
                            'company_id': self.company_id.id,
                            'datas': content.datas,
                            'store_fname': content.name,
                            'mimetype': 'application/xml'
                        }
                        attachment_list.append(attachment_data)
                    except Exception as e:
                        _logger.info(e)
                if attachment_list:
                    cfdi_ids = self.env['iia_boveda_fiscal.cfdi'].create_cfdis(attachment_list)
                    if cfdi_ids:
                        return {
                            "name": _("CFDIs importados"),
                            "view_mode": "tree,form",
                            "res_model": "iia_boveda_fiscal.cfdi",
                            "type": "ir.actions.act_window",
                            "target": "current",
                            "domain": [("id", "=", cfdi_ids.ids)]
                        }
                    else:
                        return {
                            'type': 'ir.actions.client',
                            'tag': 'display_notification',
                            'params': {
                                'title': _("No se cargaron nuevos CFDIs al sistema ya que estos ya existen o no pertenecen a la empresa, favor de validar."),
                                'type': 'warning',
                                'sticky': True,
                            },
                        }
            else:
                raise ValidationError(_('No ha subido ningún archivo XML'))
