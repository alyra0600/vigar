from odoo import models, fields, _
from odoo.exceptions import UserError


class CancelInvoiceWizard(models.TransientModel):
    _name = 'cancel.invoice.wizard'
    _description = 'Motivo de Cancelación de Factura'

    invoice_ids = fields.Many2many('account.move', string='Facturas')
    reason = fields.Char(string='Motivo de Cancelación', required=True)

    def action_cancel(self):
        if not self.invoice_ids:
            raise UserError(_('No hay facturas seleccionadas.'))
        self.invoice_ids.write({'cancellation_reason': self.reason})
        self.invoice_ids.with_context(from_cancel_wizard=True).button_cancel()
        return {'type': 'ir.actions.act_window_close'}
