# -*- coding: utf-8 -*-

from odoo import fields, models


class IrActionsReportXml(models.Model):
    """ @inherit report action model to add watermark and lastpage fields """
    _inherit = 'ir.actions.report'

    pdf_watermark = fields.Binary(
            'Watermark PDF',
            company_dependent=True,
            help=
            'Upload a watermark PDF to be used as the background of each page printed.\n\
                    Watermark uploaded here will override the one uploaded at company \
                    level in the general settings.')
    pdf_watermark_fname = fields.Char('Watermark Filename', company_dependent=True)
    pdf_last_page = fields.Binary(
            'Last Pages PDF',
            company_dependent=True,
            help=
            'Here you can upload a PDF document that contain some specific content \
                    such as product brochure,\n promotional content, advert, sale terms and\
                    Conditions,..etc.\nThis document will be appended to the printed report. \n\
                    Last pages PDF uploaded here will override the one uploaded at company \
                    level in the general settings.')
    pdf_last_page_fname = fields.Char('Last Pages Filename', company_dependent=True)
