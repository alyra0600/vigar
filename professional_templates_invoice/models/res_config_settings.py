# -*- coding: utf-8 -*-

from odoo import fields, models


class ReportConfigSettings(models.TransientModel):
    """Transient model to display settings/configs for the report in the
    general settings menu."""
    _inherit = ["res.config.settings"]

    df_style = fields.Many2one(related='company_id.df_style', readonly=False)
    pdf_watermark = fields.Binary(related='company_id.pdf_watermark',
                                  readonly=False)
    pdf_watermark_fname = fields.Char(related='company_id.pdf_watermark_fname',
                                      readonly=False)
    pdf_last_page = fields.Binary(related='company_id.pdf_last_page',
                                  readonly=False)
    pdf_last_page_fname = fields.Char(related='company_id.pdf_last_page_fname',
                                      readonly=False)
