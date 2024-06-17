# -*- coding: utf-8 -*-

from odoo import models, api, fields

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    esignature_ids = fields.Many2many(related='company_id.esignature_ids', string='MX E-signature', readonly=False)
