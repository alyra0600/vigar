from odoo import models, fields, _
from odoo.exceptions import AccessError


class AccountMove(models.Model):
    _inherit = 'account.move'

    credit_note_reason = fields.Char(string='Motivo de Nota de Crédito', copy=False)
    cancellation_reason = fields.Char(string='Motivo de Cancelación', copy=False)

    def action_reverse(self):
        if not self.env.user.has_group('iia_ventas_restricciones.group_can_create_credit_note'):
            raise AccessError(_('No tiene permiso para crear notas de crédito.'))
        return super().action_reverse()

    def button_cancel(self):
        invoice_types = ('out_invoice', 'out_refund', 'in_invoice', 'in_refund', 'out_receipt', 'in_receipt')
        if any(move.move_type in invoice_types for move in self):
            if not self.env.user.has_group('iia_ventas_restricciones.group_can_cancel_invoice'):
                raise AccessError(_('No tiene permiso para cancelar facturas.'))
            if not self.env.context.get('from_cancel_wizard'):
                return {
                    'name': _('Motivo de Cancelación'),
                    'type': 'ir.actions.act_window',
                    'res_model': 'cancel.invoice.wizard',
                    'view_mode': 'form',
                    'target': 'new',
                    'context': {'default_invoice_ids': [(6, 0, self.ids)]},
                }
        return super().button_cancel()
