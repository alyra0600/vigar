# -*- coding: utf-8 -*-

from odoo import fields, models


class ResCurrency(models.Model):
    """ Currency @model @inherit to add currency_name field for amount in words"""

    _inherit = "res.currency"

    currency_name = fields.Char('Currency Name',
                                help="Currency full name e.g US Dollars")
