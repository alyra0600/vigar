# -*- coding: utf-8 -*-
from odoo import fields, models, api

class AccountJournalFooter(models.Model):
    _inherit = 'account.journal'

    @api.model
    def _default_inv_template(self):
        def_tpl = self.env['ir.ui.view'].search(
            [('key', 'like', 'professional_templates_invoice.INVOICE\_%\_document'),
             ('type', '=', 'qweb')],
            order='key asc',
            limit=1)
        return def_tpl or self.env.ref(
            'account.report_invoice_with_payments')    

    display_on_footer = fields.Boolean(
        "Show in Invoices Footer",
        help=
        "Display this bank account on the footer of printed documents like invoices and sales orders."
    )
    df_style = fields.Many2one(
        'report.template.settings',
        'Default Style',
        help=
        "If no other report style is specified during the printing of document,\
                    this default style will be used"
    )
