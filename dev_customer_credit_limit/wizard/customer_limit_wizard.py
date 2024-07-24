# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2015 DevIntelle Consulting Service Pvt.Ltd (<http://www.devintellecs.com>).
#
#    For Module Support : devintelle@gmail.com  or Skype : devintelle
#
##############################################################################

import json
import logging
from datetime import timedelta
from collections import defaultdict

from odoo import api, fields, models, _
from odoo.tools import float_compare, float_round
from odoo.exceptions import UserError


_logger = logging.getLogger(__name__)


class customer_limit_wizard(models.TransientModel):
    _name = "customer.limit.wizard"
    _description = 'Asistente de Limite de Credito'
    
    def set_credit_limit_state(self):
        context = self._context
        model = context.get('active_model')
        record_id = self.env[model].browse(self._context.get('active_id'))
        record_id.exceeded_amount = self.exceeded_amount
        record_id.send_mail_approve_credit_limit()
        partner_id = self.partner_id
        if partner_id.parent_id:
            partner_id= partner_id.parent_id
        partner_id.credit_limit_on_hold = self.credit_limit_on_hold
        record_id.free_current_order = self.free_current_order
        if self.free_current_order:
            if model == 'sale.order':
                record_id.action_confirm()
            elif model == 'account.move':
                record_id.action_post()
        
        return True
    
    current_sale = fields.Float('Cotización Actual')
    exceeded_amount = fields.Float('Monto Excedente')
    credit = fields.Float('A cobrar')
    partner_id = fields.Many2one('res.partner',string="Cliente")
    credit_limit = fields.Float(related='partner_id.credit_limit',string="Limite de Credito")
    sale_orders = fields.Char("Pedidos de Venta")
    invoices = fields.Char("Facturas")
    credit_limit_on_hold = fields.Boolean('Limite de Credito Bloqueado')
    invoice_due_on_hold = fields.Boolean('Facturas Vencidas', help="Limite de tolerancia superado.")
    free_current_order = fields.Boolean('Liberar Pedido')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
