from odoo import models, api, fields, _


class AccountMove(models.Model):
    _inherit = 'account.move'

    def action_register_partial_payment(self, id):
        self.ensure_one()
        accout_move_line_payment = self.env['account.move.line'].browse([id])
        return {
            'name': _('Register Partial Payment'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'views': [(False, 'form')],
            'res_model': 'account.payment.partial.register',
            'target': 'new',
            'context': {
                'active_model': 'account.move',
                'active_ids': [self.id],
                'default_account_move_line_id': accout_move_line_payment.id,
                'default_account_payment_id': accout_move_line_payment.move_id.payment_id.id,
                'default_account_payment_move_id': accout_move_line_payment.move_id.id,
            },
        }

    @api.model
    def create_discount_entry(self, amount, account_id, partner_id):

        """This method creates a transaction in the account transaction
        model corresponding to the cash discount voucher """

        if amount <= 0:
            raise ValueError("The discount amount must be greater than zero.")
        if not account_id or not partner_id:
            raise ValueError("Account ID and Partner ID must be provided.")

        account = self.env['account.account'].browse(account_id)
        partner = self.env['res.partner'].browse(partner_id)

        if not account.exists() or not partner.exists():
            raise ValueError("Invalid account or partner.")

        move_vals = {
            'journal_id': self.env['account.journal'].search([('type', '=', 'general')], limit=1).id,
            'date': fields.Date.today(),
            'ref': 'Early Payment Discount',
            'line_ids': [
                (0, 0, {
                    'account_id': account.id,
                    'partner_id': partner.id,
                    'name': 'Discount for early payment',
                    'debit': amount,
                    'credit': 0,
                }),
                (0, 0, {
                    'account_id': self.env['account.account'].search([('account_type', '=', 'asset_receivable')],
                                                                     limit=1).id,
                    'partner_id': partner.id,
                    'name': 'Discount for early payment',
                    'debit': 0,
                    'credit': amount,
                }),
            ],
        }

        move = self.env['account.move'].create(move_vals)
        move.action_post()

        return move
