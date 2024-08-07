from odoo import models


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    def _prepare_reconciliation_plan(self, plan, amls_values_map, shadowed_aml_values=None):

        if bool(self._context.get('multi_partial', False)):
            for line, values in amls_values_map.items():

                if self._context.get('default_account_move_line_id') == line.id:
                    signo = -1 if line.balance < 0.0 else 1
                    amount_residual_currency = self._context.get('amount_residual') * signo
                    amount_residual = line.currency_id._convert(
                        amount_residual_currency,
                        line.company_currency_id,
                        line.company_id,
                        line.date
                    )
                    values.update({
                    'amount_residual': amount_residual,
                    'amount_residual_currency': amount_residual_currency,
                    })

        return super()._prepare_reconciliation_plan(plan, amls_values_map, shadowed_aml_values=shadowed_aml_values)
