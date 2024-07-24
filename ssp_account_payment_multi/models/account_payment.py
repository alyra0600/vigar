from odoo import _, api, fields, models


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    def _compute_amount_residual(self):
        for move_payment in self:
            amount_residual = move_payment.account_payable_or_receivable.amount_residual_currency
            move_payment.amount_residual = abs(amount_residual)

    account_payable_or_receivable = fields.Many2one('account.move.line',
                                                    compute="_compute_account_payable_or_receivable", store=False)
    matched_debit_ids = fields.One2many('account.partial.reconcile', compute='_compute_matched_ids')
    matched_credit_ids = fields.One2many('account.partial.reconcile', compute='_compute_matched_ids')
    amount_residual = fields.Monetary(compute="_compute_amount_residual", currency_field='currency_id')
    deposit_date  = fields.Date(
        string='Deposit Date',
        required=False)

    not_fiscal_payment_type  = fields.Selection(
        string='Forma de pago no fiscal',
        selection=[('efectivo', 'Efectivo'),
                   ('cheque_banorte', 'Cheque Banorte'),
                   ('cheque_banregio', 'Cheque Banoregio'),
                   ('cheque_banamex', 'Cheque Banamex'),
                   ('cheque_hsbc', 'Cheque HSBC'),
                   ('cheque_bancomer', 'Cheque Bancomer'),
                   ('cheque_afirma', 'Cheque Afirme'),
                   ('cheque_santander', 'Cheque Santander'),
                   ('tpv', 'TPV')
                  ,],
        required=False, )


    def _compute_matched_ids(self):
        domain = [('account_type', 'in', ('asset_receivable', 'liability_payable'))]
        for payment in self:
            entries_lines = payment.move_id.line_ids.filtered_domain(domain)
            payment.matched_debit_ids = entries_lines.matched_debit_ids
            payment.matched_credit_ids = entries_lines.matched_credit_ids

    @api.depends('move_id')
    def _compute_account_payable_or_receivable(self):
        domain = [('account_type', 'in', ('asset_receivable', 'liability_payable'))]
        for payment in self:
            entries_lines = payment.move_id.line_ids.filtered_domain(domain)
            payment.account_payable_or_receivable = entries_lines.id

    def action_register_multi_payment(self):
        return {
            'name': _('Register Multi Payment'),
            'res_model': 'account.payment.multi.partial.register',
            'view_mode': 'form',
            'context': {
                'active_model': 'account.payment',
                'active_ids': self.id,
            },
            'target': 'new',
            'type': 'ir.actions.act_window',
            # 'search_view_id':[self.env.ref('ssp_account_payment_multi.view_account_payment_move_search').id],
        }