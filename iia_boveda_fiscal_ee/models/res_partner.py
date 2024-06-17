# -*- coding: utf-8 -*-

from odoo import models, fields, api

class Respartner(models.Model):
	_inherit = 'res.partner'

	account_xml_id = fields.Many2one(comodel_name='account.account', string='Cuenta contable gasto')
	product_tmpl_id = fields.Many2one(comodel_name='product.template', string='Producto')
	tax_isr_id = fields.Many2one(comodel_name='account.tax', string='Retención ISR')
	tax_iva_id = fields.Many2one(comodel_name='account.tax', string='Retención IVA')
	x_is_uuid_required = fields.Boolean(string="¿Es requerido el UUID?")