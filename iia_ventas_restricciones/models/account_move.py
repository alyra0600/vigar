from odoo import models, fields, _
from odoo.exceptions import AccessError


class AccountMove(models.Model):
    _inherit = 'account.move'

    credit_note_reason = fields.Char(string='Motivo de Nota de Crédito', copy=False)
    cancellation_reason = fields.Char(string='Motivo de Cancelación', copy=False)

    def _iia_validar_permiso_cancelar(self):
        if not self.env.su and not self.env.user.has_group('iia_ventas_restricciones.group_can_cancel_invoice'):
            raise AccessError(_('No tiene permiso para cancelar facturas.'))

    def action_reverse(self):
        if not self.env.user.has_group('iia_ventas_restricciones.group_can_create_credit_note'):
            raise AccessError(_('No tiene permiso para crear notas de crédito.'))
        return super().action_reverse()

    def button_cancel(self):
        invoice_types = ('out_invoice', 'out_refund', 'in_invoice', 'in_refund', 'out_receipt', 'in_receipt')
        facturas = self.filtered(
            lambda move: move.move_type in invoice_types and move.l10n_mx_edi_cfdi_state != 'cancel'
        )
        if facturas and not self.env.su:
            facturas._iia_validar_permiso_cancelar()
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

    def button_request_cancel(self):
        self._iia_validar_permiso_cancelar()
        return super().button_request_cancel()

    def _l10n_mx_edi_cfdi_invoice_try_cancel(self, document, cancel_reason):
        self._iia_validar_permiso_cancelar()
        return super()._l10n_mx_edi_cfdi_invoice_try_cancel(document, cancel_reason)
