from odoo import models


class AccountMoveReversal(models.TransientModel):
    _inherit = 'account.move.reversal'

    def reverse_moves(self, is_modify=False):
        result = super().reverse_moves(is_modify=is_modify)
        if self.reason and self.new_move_ids:
            self.new_move_ids.write({'credit_note_reason': self.reason})
        return result
