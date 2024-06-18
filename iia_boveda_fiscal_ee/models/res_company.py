# -*- coding: utf-8 -*-

from odoo import models, api, fields, _
from odoo.exceptions import ValidationError, UserError
import base64
import time
import logging
from datetime import  date, datetime
from dateutil.relativedelta import relativedelta
from .esignature import convert_key_cer_to_pem
from .portal_sat import PortalSAT
from cfdiclient import (Autenticacion, DescargaMasiva, Fiel, SolicitaDescarga, VerificaSolicitudDescarga)
from zipfile import ZipFile


_logger = logging.getLogger(__name__)
TRY_COUNT = 3

class ResCompany(models.Model):
    _inherit = 'res.company'

    esignature_ids = fields.Many2many('iia_boveda_fiscal.esignature.certificate', string='Certificado FIEL')
    last_cfdi_fetch_date = fields.Datetime("Última sincronización")
    solo_documentos_de_proveedor = fields.Boolean("Solo documentos de proveedor")
    
    @api.model
    def auto_import_cfdi_invoices(self):
        for company in self.search([('esignature_ids', '!=', False)]):
            company.with_company(company.id).download_cfdi_invoices_sat()
        return True
    
    def import_sat(self, start_date=False, end_Date=False, document_type=False):
        certificates = self.esignature_ids
        certificate = certificates.sudo().get_valid_certificate()
        
        cer_der = base64.b64decode(certificate.content)
        key_der = base64.b64decode(certificate.key)
        
        rfc = self.vat
        
        # RFC = 'MCD811204E7A'
        # FIEL_CER = '00001000000511191739.cer'
        # FIEL_KEY = 'Claveprivada_FIEL_MCD811204E7A_20220202_181045.key'
        # FIEL_PAS = 'MCD811204E7A'
        # FECHA_INICIAL = datetime.date(2022, 2, 1)
        # FECHA_FINAL = datetime.date(2022, 2, 1)
        # PATH = 'MCD811204E7A/'
        # cer_der = open(os.path.join(PATH, FIEL_CER), 'rb').read()
        # key_der = open(os.path.join(PATH, FIEL_KEY), 'rb').read()
        
        fiel = Fiel(cer_der, key_der, certificate.password.encode('UTF-8'))
        auth = Autenticacion(fiel)
        token = auth.obtener_token()
        _logger.info('TOKEN: %s', token)
        
        # EMITIDOS
        if document_type == '0' or self.type == '1':
            _logger.info("INICIO EMITIDOS")
            _logger.info("===============")
            descarga = SolicitaDescarga(fiel)
            solicitud = descarga.solicitar_descarga(token, rfc, start_date, end_Date, rfc_emisor=rfc, tipo_solicitud='CFDI')
            self.descargar_solicitud(solicitud, auth, fiel, rfc)
            _logger.info("  FIN EMITIDOS")
            _logger.info("===============")
        
        # RECIBIDOS
        if document_type == '0' or document_type == '2':
            _logger.info("INICIO RECIBIDOS")
            _logger.info("===============")
            descarga = SolicitaDescarga(fiel)
            solicitud = descarga.solicitar_descarga(
                token, rfc, start_date, end_Date, rfc_receptor=rfc, tipo_solicitud='CFDI'
            )
            self.descargar_solicitud(solicitud, auth, fiel, rfc)
            _logger.info("  FIN RECIBIDOS")
            _logger.info("===============")
    
    def descargar_solicitud(self, solicitud, auth, fiel, rfc):
        
        _logger.info('SOLICITUD: %s', solicitud)
        repetir = 0
        filename = False
        while True:
            token = auth.obtener_token()
            _logger.info('TOKEN: %s', token)
            verificacion = VerificaSolicitudDescarga(fiel)
            verificacion = verificacion.verificar_descarga(
                token, rfc, solicitud['id_solicitud'])
            _logger.info('SOLICITUD: %s', verificacion)
            estado_solicitud = int(verificacion['estado_solicitud'])
            
            # 0, Token invalido.
            # 1, Aceptada
            # 2, En proceso
            # 3, Terminada
            # 4, Error
            # 5, Rechazada
            # 6, Vencida
            
            if estado_solicitud == 0:
                break
            elif estado_solicitud <= 2:
                # Si el estado de solicitud esta Aceptado o en proceso el programa espera
                # 60 segundos y vuelve a tratar de verificar
                if repetir < 3:
                    repetir = repetir + 1
                    time.sleep(60)
                    continue
                else:
                    _logger.info('ERROR: Número de intentos')
                    break
            elif estado_solicitud >= 4:
                _logger.info('ERROR: %s', estado_solicitud)
                break
            else:
                # Si el estatus es 3 se trata de descargar los paquetes
                for paquete in verificacion['paquetes']:
                    descarga = DescargaMasiva(fiel)
                    descarga = descarga.descargar_paquete(token, rfc, paquete)
                    _logger.info('PAQUETE: %s', paquete)
                    filename = '/tmp/{}.zip'.format(paquete)
                    with open(filename, 'wb') as fp:
                        fp.write(base64.b64decode(descarga['paquete_b64']))
                break
        
        if filename:
            zip_file = ZipFile(filename, 'r')
            files = zip_file.namelist()
            for file_extract in files:
                with zip_file.open(file_extract) as file:
                    xml_content = file.read()
                    attachment_id = self.env['ir.attachment'].create({
                        'name': file_extract,
                        'type': 'binary',
                        'company_id': self.id,
                        'datas': base64.b64encode(xml_content),
                        'store_fname': file_extract,
                        'mimetype': 'application/xml'
                    })
                    if attachment_id:
                        # Corrige el nombre del CFDI tanto el codigo como el adjunto
                        
                        cfdi_id = self.env['iia_boveda_fiscal.cfdi'].create({
                            'attachment_id': attachment_id.id
                        })
    

    def download_cfdi_invoices_sat(self, start_date=False, end_Date=False, document_type=False):
        esignature_ids = self.esignature_ids
        esignature = esignature_ids.with_user(self.env.user).get_valid_certificate()
        if not esignature:
            raise ValidationError("Archivos incorrectos no son una FIEL.")

        if not esignature.content or not esignature.key or not esignature.password:
            raise ValidationError("Seleccine los archivos FIEL .cer o FIEL .pem.")

        fiel_cert_data = base64.b64decode(esignature.content)
        fiel_pem_data = convert_key_cer_to_pem(esignature.key, esignature.password)

        opt = {'credenciales': None, 'rfc': None, 'uuid': None, 'ano': None, 'mes': None, 'dia': 0,
               'intervalo_dias': None, 'fecha_inicial': None, 'fecha_final': None, 'tipo': 't',
               'tipo_complemento': '-1', 'rfc_emisor': None, 'rfc_receptor': None, 'sin_descargar': False,
               'base_datos': False, 'directorio_fiel': '', 'archivo_uuids': '', 'estatus': False}
        today = datetime.utcnow()
        if start_date and end_Date:
            opt['fecha_inicial'] = datetime.combine(start_date, datetime.min.time())
            opt['fecha_final'] = datetime.combine(end_Date, datetime.max.time())
        elif self.last_cfdi_fetch_date:
            last_import_date = self.last_cfdi_fetch_date
            last_import_date - relativedelta(days=2)

            fecha_inicial = last_import_date - relativedelta(days=2)
            fecha_final = today + relativedelta(days=2)
            opt['fecha_inicial'] = fecha_inicial
            opt['fecha_final'] = fecha_final
        else:
            year = today.year
            month = today.month
            opt['ano'] = year
            opt['mes'] = month

        sat = False
        for i in range(TRY_COUNT):
            sat = PortalSAT(opt['rfc'], 'cfdi-descarga', False)
            if sat.login_fiel(fiel_cert_data, fiel_pem_data):
                time.sleep(1)
                break
        invoice_content_receptor, invoice_content_emisor = {}, {}
        if sat and sat.is_connect:
            if document_type == "supplier":
                invoice_content_receptor, invoice_content_emisor = sat.search(opt, 'supplier')
            elif document_type == "customer":
                invoice_content_receptor, invoice_content_emisor = sat.search(opt, 'customer')
            else:
                invoice_content_receptor, invoice_content_emisor = sat.search(opt)
            sat.logout()
        elif sat:
            sat.logout()

        attachment_data = []
        if invoice_content_receptor:
            attachment_data += self.get_cfdi_data(invoice_content_receptor, attachment_data)
        if invoice_content_emisor:
            attachment_data += self.get_cfdi_data(invoice_content_emisor, attachment_data)
        if attachment_data:
            cfdi_ids = self.env['iia_boveda_fiscal.cfdi'].create_cfdis(attachment_data=attachment_data)
            if cfdi_ids:
                self.write({'last_cfdi_fetch_date': date.today()})
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
                        'title': _("No se cargaron nuevos CFDIs al sistema ya que estos ya existen o no se encontraron, favor de validar."),
                        'type': 'warning',
                        'sticky': True,
                    },
                }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _("No se encontraron CFDIs que coincidan con las fechas o estos ya se encuentran en el sistema, favor de validar."),
                    'type': 'warning',
                    'sticky': True,
                },
            }

    def get_cfdi_data(self, content_sat, attachment_data):
        uuids = list(content_sat.keys())
        cfdi_ids = self.env["iia_boveda_fiscal.cfdi"].sudo().search([('uuid', 'in', uuids)])
        exist_uuids = cfdi_ids.mapped('uuid')

        for uuid, data in content_sat.items():
            if uuid in exist_uuids:
                continue
            xml_content = data[1]
            filename = uuid + ".xml"
            data = dict(
                name=filename,
                store_fname=filename,
                type='binary',
                datas=base64.b64encode(xml_content),
                company_id=self.id,
                mimetype='application/xml'
            )
            attachment_data.append(data)
        return attachment_data
