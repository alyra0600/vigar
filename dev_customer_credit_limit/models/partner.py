# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2015 DevIntelle Consulting Service Pvt.Ltd (<http://www.devintellecs.com>).
#
#    For Module Support : devintelle@gmail.com  or Skype : devintelle
#
##############################################################################

from odoo import models, fields

class res_partner(models.Model):
    _inherit= 'res.partner'
    
    check_credit = fields.Boolean('Activar Credito')
    credit_limit_on_hold  = fields.Boolean('Bloqueado por Limite de Credito')
    credit_limit = fields.Float('Limite de Credito')
    tolerance_max_invoice_due = fields.Integer('Tolerancia dias vencimiento')
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: