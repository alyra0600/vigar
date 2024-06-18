# -*- coding: utf-8 -*-

from odoo import fields, models


class ReportDefaultSettings(models.Model):
    """ @inherit company @model to add fields for report settings"""
    _inherit = ["res.company"]

    facebook = fields.Char('Facebook ID')
    twitter = fields.Char('Twitter Handle')
    youtube = fields.Char('YouTube ID')

    df_style = fields.Many2one(
        'report.template.settings',
        'Default Style',
        help=
        "If no other report style is specified during the printing of document,\
                    this default style will be used")

    pdf_watermark = fields.Binary(
        'Watermark PDF',
        help=
        'Upload your company letterhead PDF or a PDF to form the background of your reports.\
                    This PDF will be used as the background of each an every page printed.'
    )

    pdf_watermark_fname = fields.Char('Watermark Filename')

    pdf_last_page = fields.Binary(
        'Last Pages PDF',
        help=
        'Here you can upload a PDF document that contain some specific content \
                    such as product brochure,\n promotional content, advert, sale terms \
                    and Conditions,..etc.\n This document will be appended to the printed report'
    )
    pdf_last_page_fname = fields.Char('Last Pages Filename')
