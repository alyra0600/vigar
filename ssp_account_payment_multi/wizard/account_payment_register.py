# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.tools.misc import formatLang
from odoo.exceptions import ValidationError
from odoo.tools import float_is_zero


# este es elwizard que se llama desde la factura
class AccountPaymentPartialRegister(models.TransientModel):
    _name = 'account.payment.partial.register'
    _description = 'Register Partial Payment'

    payment_id = fields.Many2one('account.payment')
    # Movimineot de facturacion line?ids

    # == Business fields ==
    payment_line_ids = fields.One2many(related='payment_id.line_ids')

    active_move_id = fields.Many2one('account.move', string="Document Active")
    active_move_type = fields.Selection(related='active_move_id.move_type')
    active_move_partner = fields.Many2one(related='active_move_id.partner_id')
    active_move_date = fields.Date(related='active_move_id.invoice_date')
    active_move_date_due = fields.Date(related='active_move_id.invoice_date_due')
    active_move_currency = fields.Many2one(related='active_move_id.currency_id')
    active_move_total = fields.Monetary(related='active_move_id.amount_total', currency_field='active_move_currency')
    active_move_residual = fields.Monetary(related='active_move_id.amount_residual',
                                           currency_field='active_move_currency')

    name = fields.Char(related='payment_id.name')
    company_id = fields.Many2one(related='payment_id.company_id')
    company_currency_id = fields.Many2one(related='company_id.currency_id', string="Company Currency")
    journal_id = fields.Many2one(related='payment_id.journal_id')
    date_payment = fields.Date(related='payment_id.date')
    ref = fields.Char(related='payment_id.ref')

    is_reconciled = fields.Boolean(related='payment_id.is_reconciled')
    is_matched = fields.Boolean(related='payment_id.is_matched')
    # == Payment methods fields ==

    # == Synchronized fields with the account.move.lines ==
    payment_type = fields.Selection(related='payment_id.payment_type')
    partner_type = fields.Selection(related='payment_id.partner_type')
    payment_reference = fields.Char(related='payment_id.payment_reference')
    payment_currency_id = fields.Many2one(related='payment_id.currency_id', string="Currenvy Payment")

    partner_id = fields.Many2one(related='payment_id.partner_id')
    destination_account_id = fields.Many2one(related='payment_id.destination_account_id')

    # == Display purpose fields ==
    entries_pay_move_id = fields.Many2one('account.move')
    account_payable_or_receivable = fields.Many2one('account.move.line')
    matched_debit_ids = fields.One2many(related='account_payable_or_receivable.matched_debit_ids')
    matched_credit_ids = fields.One2many(related='account_payable_or_receivable.matched_credit_ids')
    amount = fields.Monetary(related="payment_id.amount", string="Amount Payment", currency_field='payment_currency_id',
                             readonly=True)
    amount_residual = fields.Monetary(string="Aavailable Amount", compute="_compute_amount_residual",
                                      currency_field='payment_currency_id', readonly=True)
    amount_partial = fields.Monetary(string='Partial Amount', currency_field='payment_currency_id')

    @api.depends('amount', 'account_payable_or_receivable', 'matched_debit_ids', 'matched_credit_ids')
    def _compute_amount_residual(self):
        self.ensure_one()
        amount_residual = abs(self.account_payable_or_receivable.amount_residual_currency)
        sum_partial_amount = 0.0
        self.amount_residual = abs(amount_residual) - abs(sum_partial_amount)

    # ---------------------------------------------------------------------
    # LOW-LEVEL METHODS
    # -------------------------------------------------------------------------
    @api.model
    def default_get(self, fields):

        result = super(AccountPaymentPartialRegister, self).default_get(fields)

        # Linea move line
        context_move_line_id = self.env.context.get('default_account_move_line_id')
        context_account_payment_id = self.env.context.get('default_account_payment_id')
        context_active_move_id = self._context.get('active_ids', [])
        context_account_payment_move_id = self._context.get('default_account_payment_move_id')

        # Asiento contable entrada Payment
        # entries_pay_move_id = self.env['account.move'].browse(context_entries_pay_move_id)
        # Apunte Contable de cuentas por cobrar/pagar del Pago
        account_payable_or_receivable = self.env['account.move.line'].browse(context_move_line_id)
        # Asiento contable de factura
        # active_move_id = self.env['account.move'].browse(context_active_move_id)

        result.update({
            'account_payable_or_receivable': context_move_line_id,  # apunte contable de cuenta por paga o cobrar
            'entries_pay_move_id': context_account_payment_move_id,  # Asiento contable del pago, move_id, partida doble
            'payment_id': context_account_payment_id,  # Pago account payment
            'active_move_id': context_active_move_id[0] if context_active_move_id else None,  # Account move Factura
        })
        return result

    def create_partial_payment(self, active_move_id, payment_move_id):

        domain = [('account_type', 'in', ('asset_receivable', 'liability_payable'))]

        # Cuenta por cobrar o pagar de la factura
        account_payable_or_receivable = active_move_id.line_ids.filtered_domain(domain)
        to_reconcile = [account_payable_or_receivable]

        payments = payment_move_id

        # to_reconcile_payments = [payments.line_ids.filtered_domain(domain)]
        signo = None
        if self.payment_type == 'inbound' and self.partner_type == 'customer':
            signo = -1
        if self.payment_type == 'outbound' and self.partner_type == 'customer':
            signo = 1
        if self.payment_type == 'inbound' and self.partner_type == 'supplier':
            signo = 1
        if self.payment_type == 'outbound' and self.partner_type == 'supplier':
            signo = -1

        amount_residual = self.amount_partial
        for payment, lines in zip(payments, to_reconcile):

            payment_lines = payment.line_ids.filtered_domain(domain)
            payment_lines = payment_lines.with_context(amount_residual=amount_residual, multi_partial=True)
            for account in payment_lines.account_id:
                move_lines = (payment_lines + lines) \
                    .filtered_domain([('account_id', '=', account.id)])
                move_lines.reconcile()
        return True

    def _create_payments_partial(self):
        self.ensure_one()
        for record in self.payment_id:
            if float_is_zero(self.amount_partial, precision_rounding=self.active_move_currency.rounding):
                continue
            # get el move id,  factura a la cual se le abonara el pago
            payment_move_id = record.move_id
            # get el amount partial, captura el monto partial abonado
            amount_partial = 0.0
            self.create_partial_payment(self.active_move_id, payment_move_id)
        return True

    def action_create_payments(self):

        if self.amount_partial > self.amount:
            raise ValidationError(_("The partial amount cannot be greater than the  amount in invoices"))

        if self.amount_partial <= 0:
            raise ValidationError(_("The partial amount cannot be zero"))

        payments = self._create_payments_partial()

        action = {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id': self.active_move_id.id,
        }
        return action


class AccountPaymentPartial(models.TransientModel):
    _name = 'account.payment.partial'
    _description = 'Document Account Payment Partial'

    wizard_id = fields.Many2one('account.payment.multi.partial.register')
    wizard_2_id = fields.Many2one('account.payment.multi.partial.register.list')
    payment_id = fields.Many2one(related='wizard_id.payment_id')
    payment_type = fields.Selection(related='payment_id.payment_type')
    partner_type = fields.Selection(related='payment_id.partner_type')
    partner_id = fields.Many2one(related='payment_id.partner_id')
    move_id = fields.Many2one('account.move', string='Document')

    # domain_move_id = fields.Many2one(compute="_compute_domain_move_id", readonly=True, store=False)
    currency_id = fields.Many2one(related='move_id.currency_id', string="Currency")
    payment_currency_id = fields.Many2one(related='payment_id.currency_id', string="Moneda Pago")
    company_id = fields.Many2one(related='payment_id.company_id', string="Company")
    company_currency_id = fields.Many2one(related='company_id.currency_id', string="COmpany Currency")

    origin = fields.Char(related='move_id.invoice_origin')
    date_invoice = fields.Date(related='move_id.invoice_date')
    date_due = fields.Date(related='move_id.invoice_date_due')
    payment_state = fields.Selection(related='payment_id.state', store=True)
    partial_amount = fields.Monetary(readonly=False)
    amount_total = fields.Monetary(related="move_id.amount_total", string="Total Currency")
    amount_total_signed = fields.Monetary(related="move_id.amount_total_signed", string="Total Company Currency")

    amount_untaxed_signed = fields.Monetary(related="move_id.amount_untaxed_signed", string="Untaxed Company Currency")
    amount_tax_signed = fields.Monetary(related="move_id.amount_tax_signed", string="Tax Company Currency")
    residual = fields.Monetary(related="move_id.amount_residual", string="Residual Currency")
    amount_residual_signed = fields.Monetary(related="move_id.amount_residual_signed",
                                             string="Residual Company Currency")

    payment_difference = fields.Monetary(currency_field='currency_id', string='Diferencias')
    difference_management = fields.Selection(
        string='Manejo de Diferencias',
        selection=[('keep_open', 'Keep open'),
                   ('mark_as_paid', 'Mark as paid'), ],
        required=False, deafult='keep_open')

    destination_account_2_id = fields.Many2one(
        comodel_name='account.account',
        string='Cuenta de diferencias',
        required=False)

    account_tag = fields.Many2many(
        comodel_name='account.account.tag',
        string='Etiqueta')

    domain_payment_move_ids = fields.Many2many(
        comodel_name="account.move",
        compute="_compute_domain_payment_move_ids",
        string="Domain Move Id",
    )

    @api.model
    def default_get(self, fields):
        result = super().default_get(fields)

        result.update({
            'partial_amount': self.amount_total,  # Pago account payment
        })
        return result

    @api.onchange('partial_amount')
    def _onchange_partial_amount(self):
        self.payment_difference = self.residual - self.partial_amount

    @api.depends('partner_id')
    def _compute_domain_payment_move_ids(self):
        account_move = self.env['account.move']
        for record in self:
            if record.payment_type == 'inbound' and record.partner_type == 'customer':
                domain = account_move.search(
                    [('partner_id', '=', record.partner_id.id), ('payment_state', 'in', ('not_paid', 'partial')),
                     ('state', '=', 'posted'), ('move_type', 'in', ('out_invoice', 'out_receipt'))])
            elif record.payment_type == 'outbound' and record.partner_type == 'customer':
                domain = account_move.search(
                    [('partner_id', '=', record.partner_id.id), ('payment_state', 'in', ('not_paid', 'partial')),
                     ('state', '=', 'posted'), ('move_type', '=', 'out_refund')])
            elif record.payment_type == 'outbound' and record.partner_type == 'supplier':
                domain = account_move.search(
                    [('partner_id', '=', record.partner_id.id), ('payment_state', 'in', ('not_paid', 'partial')),
                     ('state', '=', 'posted'), ('move_type', 'in', ('in_invoice', 'in_receipt'))])
            else:
                domain = account_move.search(
                    [('partner_id', '=', record.partner_id.id), ('payment_state', 'in', ('not_paid', 'partial')),
                     ('state', '=', 'posted'), ('move_type', '=', 'in_refund')])
            record.domain_payment_move_ids = domain.ids


class AccountPaymentMultiPartialRegister(models.TransientModel):
    _name = 'account.payment.multi.partial.register'
    _description = 'Register Multi Partial Payment'

    @api.depends('payment_id', 'amount')
    def _compute_account_payable_or_receivable(self):
        domain = [('account_type', 'in', ('asset_receivable', 'liability_payable'))]
        for payment in self:
            entries_lines = payment.payment_id.move_id.line_ids.filtered_domain(domain)
            payment.account_payable_or_receivable = entries_lines.id

    payment_id = fields.Many2one('account.payment')
    # Movimineot de facturacion line?ids
    amount = fields.Monetary(related='payment_id.amount')
    payment_type = fields.Selection(related='payment_id.payment_type')
    partner_type = fields.Selection(related='payment_id.partner_type')
    currency_id = fields.Many2one(related='payment_id.currency_id')

    date_payment = fields.Date(related='payment_id.date')

    partner_id = fields.Many2one(related='payment_id.partner_id')
    destination_account_id = fields.Many2one(related='payment_id.destination_account_id')
    payment_move_ids = fields.One2many('account.payment.partial', 'wizard_id',
                                       string="Document Sale/Purchase",
                                       readonly=False)
    account_payable_or_receivable = fields.Many2one('account.move.line',
                                                    compute="_compute_account_payable_or_receivable", store=True)

    # amount_total_current = fields.Monetary(compute="compute_amount_residual_account", currency_field='currency_id')
    amount_residual = fields.Monetary(compute="_compute_amount_residual", currency_field='currency_id')

    @api.depends('payment_move_ids.partial_amount')
    def _compute_amount_residual(self):
        for line in self.payment_move_ids:

            if line.currency_id.id != self.payment_id.currency_id.id:
                partial_amount = self.payment_id.currency_id._convert(
                    line.partial_amount,
                    line.company_id.currency_id,
                    line.company_id,
                    self.payment_id.date
                )
            else:
                partial_amount = line.partial_amount

            if line.move_id and abs(line.amount_residual_signed) < partial_amount:
                partial_amount_value = formatLang(self.env, self.currency_id.round(partial_amount),
                                                  currency_obj=self.currency_id)
                residual = formatLang(self.env, self.currency_id.round(line.residual), currency_obj=self.currency_id)
                raise ValidationError(
                    _('Amount entered {pav} is greater than the invoice debt {lmn} {rsdl}').format(
                        pav=str(partial_amount_value), lmn=str(line.move_id.name), rsdl=str(residual))
                )
        amount_residual = abs(self.account_payable_or_receivable.amount_residual_currency)
        sum_partial_amount = sum(self.payment_move_ids.mapped('partial_amount'))

        if amount_residual < sum_partial_amount:
            raise ValidationError(_("The sum of your partial amounts is greater than the remaining amount available."))
        self.amount_residual = abs(amount_residual) - abs(sum_partial_amount)

    @api.onchange('payment_type', 'partner_type', 'partner_id', 'currency_id')
    def _onchange_to_get_vendor_invoices(self):
        if self.payment_type in ['inbound', 'outbound'] and self.partner_type and self.partner_id and self.currency_id:
            self.payment_move_ids = [(6, 0, [])]
            if self.payment_type == 'inbound' and self.partner_type == 'customer':
                invoice_type = 'out_invoice'
            elif self.payment_type == 'outbound' and self.partner_type == 'customer':
                invoice_type = 'out_refund'
            elif self.payment_type == 'outbound' and self.partner_type == 'supplier':
                invoice_type = 'in_invoice'
            else:
                invoice_type = 'in_refund'
            move_recs = self.env['account.move'].search([
                ('partner_id', 'child_of', self.partner_id.id),
                ('state', '=', 'posted'),
                ('payment_state', 'in', ('not_paid', 'partial')),
                ('move_type', '=', invoice_type),
                ('currency_id', '=', self.currency_id.id)])

            payment_move_values = [
                (0, 0, {'move_id': line.id, 'payment_id': self.payment_id.id, 'partner_id': self.partner_id.id}) for
                line in move_recs]
            self.payment_move_ids = payment_move_values

    # ---------------------------------------------------------------------
    # LOW-LEVEL METHODS
    # -------------------------------------------------------------------------
    @api.model
    def default_get(self, fields):
        result = super().default_get(fields)
        # Linea move line
        context_payment_move_id = self._context.get('active_ids', [])
        result.update({
            'payment_id': context_payment_move_id,  # Pago account payment
        })
        return result

    def create_partial_payment(self, move_id, amount_partial):
        # Cuenta por cobrar o pagar del pago
        to_reconcile = [self.account_payable_or_receivable]

        # Factura activa a pagar
        invoice_move_id = move_id
        domain = [('account_type', 'in', ('asset_receivable', 'liability_payable')),('debit', '!=', 0)]
        # to_reconcile_payments = [payments.line_ids.filtered_domain(domain)]
        signo = None
        if self.payment_type == 'inbound' and self.partner_type == 'customer':
            signo = -1
        if self.payment_type == 'outbound' and self.partner_type == 'customer':
            signo = 1
        if self.payment_type == 'inbound' and self.partner_type == 'supplier':
            signo = 1
        if self.payment_type == 'outbound' and self.partner_type == 'supplier':
            signo = -1

        for payment, lines in zip(invoice_move_id, to_reconcile):

            invoice_lines = invoice_move_id.line_ids.filtered_domain(domain)
            invoice_lines = invoice_lines.with_context(default_account_move_line_id=lines.id,
                                                       amount_residual=amount_partial, multi_partial=True)

            for account in invoice_lines.account_id:
                move_lines = (invoice_lines + lines) \
                    .filtered_domain([('account_id', '=', account.id),])
                move_lines.reconcile()

        return True

    def _create_payments_partial(self):
        self.ensure_one()
        for record in self.payment_move_ids:
            if float_is_zero(record.partial_amount, precision_rounding=self.currency_id.rounding):
                continue

            self.create_partial_payment(record.move_id, record.partial_amount)
        return True

    def action_create_payments(self):
        action = {
            'type': 'ir.actions.act_window',
            'res_model': 'account.payment',
            'view_mode': 'form',
            'res_id': self.payment_id.id,
        }

        if not self.payment_move_ids:
            return action

        if float_is_zero(sum(self.payment_move_ids.mapped('partial_amount')),
                         precision_rounding=self.currency_id.rounding):
            raise ValidationError(_("All partial amounts is zero."))

        if self.amount_residual < 0:
            raise ValidationError(_("The sum of your partial amounts is greater than the remaining amount available."))

        payments = self._create_payments_partial()

        return action


class AccountPaymentMultiPartialRegister(models.TransientModel):
    _name = 'account.payment.multi.partial.register.list'
    _description = 'Register Multi Partial Payment List'

    name = fields.Char(
        string='Name', default='Pago Múltiple',
        required=False)
    payment_id = fields.Many2one('account.payment')
    amount = fields.Monetary(String='Amount')
    currency_id = fields.Many2one(
        comodel_name='res.currency',
        string='Currency',
        required=False)
    partner_id = fields.Many2one(
        comodel_name='res.partner',
        string='Partner',
        required=False)
    destination_account_id = fields.Many2one(related='payment_id.destination_account_id')
    payment_move_ids = fields.One2many('account.payment.partial', 'wizard_2_id',
                                       string="Document Sale/Purchase",
                                       readonly=False)

    journal_id = fields.Many2one('account.journal', string='Journal', default=lambda self: self._default_journal_id(),
                                 domain="[('type', 'in', ('bank','cash'))]", )
    account_payable_or_receivable = fields.Many2one('account.move.line',
                                                    store=True)
    not_fiscal_payment_type = fields.Selection(
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
            , ],
        required=False, )
    date = fields.Date(
        string='Date', default=fields.Date.context_today,
        required=False)

    deposit_date = fields.Date(
        string='Deposit Date', default=fields.Date.context_today,
        required=False)

    @api.model
    def _default_journal_id(self):
        company = self.env.company

        bank_journal = self.env['account.journal'].search([
            ('type', '=', 'bank'),
            ('company_id', '=', company.id)
        ], limit=1)

        return bank_journal.id if bank_journal else False

    l10n_mx_edi_payment_method_id = fields.Many2one(
        comodel_name='l10n_mx_edi.payment.method', required='True',
        string="Payment Way",
        help="Indicates the way the payment was/will be received, where the options could be: "
             "Cash, Nominal Check, Credit Card, etc.")

    available_payment_method_line_ids = fields.Many2many(
        'account.payment.method.line',
        compute='_compute_payment_method_line_fields'
    )
    payment_method_line_id = fields.Many2one(
        'account.payment.method.line', required='True', domain="[('id', 'in', available_payment_method_line_ids)]",
        string=u'Método de pago',
    )

    payment_type = fields.Selection([
        ('outbound', 'Send'),
        ('inbound', 'Receive'),
    ], string='Payment Type', default='inbound', required=True)
    partner_type = fields.Selection([
        ('customer', 'Customer'),
        ('supplier', 'Vendor'),
    ], default='customer', required=True)

    @api.depends('journal_id')
    def _compute_payment_method_line_fields(self):
        for record in self:
            record.available_payment_method_line_ids = record.journal_id._get_available_payment_method_lines(
                'inbound')

    @api.onchange('l10n_mx_edi_payment_method_id')
    def _onchange_l10n_mx_edi_payment_method_id(self):
        for record in self:
            if record.l10n_mx_edi_payment_method_id:
                if record.l10n_mx_edi_payment_method_id.code in ['04', '28']:
                    payment_method_id = self.env['account.payment.method'].search(
                        [('code', '=', 'batch_payment'), ('payment_type', '=', 'inbound')], limit=1)
                    payment_method_line_id = self.env['account.payment.method.line'].search(
                        [('payment_method_id', '=', payment_method_id.id),
                         ('journal_id', '=', record.journal_id.id)], limit=1)
                    record.payment_method_line_id = payment_method_line_id.id
                else:
                    payment_method_id = self.env['account.payment.method'].search(
                        [('code', '=', 'manual'), ('payment_type', '=', 'inbound')], limit=1)
                    payment_method_line_id = self.env['account.payment.method.line'].search(
                        [('payment_method_id', '=', payment_method_id.id),
                         ('journal_id', '=', record.journal_id.id)], limit=1)
                    record.payment_method_line_id = payment_method_line_id.id

    # ---------------------------------------------------------------------
    # LOW-LEVEL METHODS
    # -------------------------------------------------------------------------
    @api.model
    def default_get(self, fields):

        result = super().default_get(fields)
        context_move_ids = self._context.get('active_ids', [])
        if len(context_move_ids) == 0:
            raise ValidationError(_('You must select an invoice from the list to process a partial payment.'))
        move_recs = self.env['account.move'].browse(context_move_ids)

        for move in move_recs:
            if move.payment_state not in ('not_paid', 'partial') or move.state != 'posted':
                raise ValidationError(
                    _('Only invoices with payment state "not paid" or "partial" and state "posted" can be processed.'))

        partner_ids = set(move.partner_id.id for move in move_recs)
        if len(partner_ids) > 1:
            raise ValidationError(_('The selected invoices must be from the same client.'))

        move_values = [
            (0, 0, {'move_id': move.id, 'difference_management': 'keep_open', 'partner_id': self.partner_id.id}) for
            move in move_recs]
        partner_id = move_recs[0].partner_id if move_recs else None
        currency_id = move_recs[0].currency_id.id if move_recs else None
        amount = sum(move.amount_total for move in move_recs)
        result.update({
            'amount': amount,
            'payment_move_ids': move_values,  # Pago account payment
            'partner_id': partner_id.id,
            'currency_id': currency_id
        })
        return result

    def create_partial_payment(self, move_id, amount_partial):
        # Cuenta por cobrar o pagar del pago
        to_reconcile = [self.account_payable_or_receivable]

        # Factura activa a pagar
        invoice_move_id = move_id
        domain = [('account_type', 'in', ('asset_receivable', 'liability_payable')),('debit', '!=', 0)]
        # to_reconcile_payments = [payments.line_ids.filtered_domain(domain)]
        signo = None
        if self.payment_type == 'inbound' and self.partner_type == 'customer':
            signo = -1
        if self.payment_type == 'outbound' and self.partner_type == 'customer':
            signo = 1
        if self.payment_type == 'inbound' and self.partner_type == 'supplier':
            signo = 1
        if self.payment_type == 'outbound' and self.partner_type == 'supplier':
            signo = -1

        for payment, lines in zip(invoice_move_id, to_reconcile):

            invoice_lines = invoice_move_id.line_ids.filtered_domain(domain)
            invoice_lines = invoice_lines.with_context(default_account_move_line_id=lines.id,
                                                       amount_residual=amount_partial, multi_partial=True)
            for line in invoice_lines:
                # Verificar si la línea ya está conciliada
                if line.reconciled:
                    print(f"La línea de la factura {line.move_id.name} ya está conciliada.")
                else:
                    print(f"La línea de la factura {line.move_id.name} no está conciliada.")

            for account in invoice_lines.account_id:
                move_lines = (invoice_lines + lines) \
                    .filtered_domain([('account_id', '=', account.id)])
                move_lines.reconcile()

        return True

    def _create_payments_partial(self):
        self.ensure_one()
        for record in self.payment_move_ids:
            if float_is_zero(record.partial_amount, precision_rounding=self.currency_id.rounding):
                continue

            self.create_partial_payment(record.move_id, record.partial_amount)
        return True

    def action_create_payments(self):

        for payment in self.payment_move_ids:
            invoice = payment.move_id
            if invoice.move_type in ('out_invoice', 'out_receipt') and self.payment_type != 'inbound':
                raise UserError('For customer invoices, payment type must be "Inbound".')
            if invoice.move_type in ('in_invoice', 'in_receipt') and self.payment_type != 'outbound':
                raise UserError(_('For supplier invoices, payment type must be "Outbound".'))

        if not self.payment_move_ids:
            raise ValidationError(_("You must add an invoice to confirm a payment"))

        residual_amount = sum(self.payment_move_ids.mapped('residual'))
        partial_amount = sum(self.payment_move_ids.mapped('partial_amount'))
        if residual_amount < partial_amount:
            raise ValidationError(
                _("The sum of the partial payments cannot be greater than the total amount of the invoices."))

        if float_is_zero(sum(self.payment_move_ids.mapped('partial_amount')),
                         precision_rounding=self.currency_id.rounding):
            raise ValidationError(_("All partial amounts is zero."))

        # Crear un nuevo registro de pago
        payment = self.env['account.payment'].create({
            'partner_id': self.partner_id.id,
            'amount': partial_amount,
            'currency_id': self.currency_id.id,
            'payment_type': self.payment_type,
            'partner_type': self.partner_type,
            'journal_id': self.journal_id.id,
            'date': fields.Date.today(),
            'payment_method_line_id': self.payment_method_line_id.id,
            'l10n_mx_edi_payment_method_id': self.l10n_mx_edi_payment_method_id.id,
            'not_fiscal_payment_type': self.not_fiscal_payment_type,
            'date': self.date,
            'deposit_date': self.deposit_date
        })

        action = {
            'type': 'ir.actions.act_window',
            'res_model': 'account.payment',
            'view_mode': 'form',
            'res_id': payment.id,
        }

        payment.action_post()
        domain = [('account_type', 'in', ('asset_receivable', 'liability_payable'))]

        entries_lines = payment.payment_id.move_id.line_ids.filtered_domain(domain)
        self.account_payable_or_receivable = entries_lines.id
        self.payment_id = payment

        # Asociar los movimientos de cuenta con el registro de pago
        for move_line in self.payment_move_ids.move_id.line_ids:
            move_line.write({'payment_id': payment.id})

        payments = self._create_payments_partial()
        # Crear descuentopor pronto pago.
        for move in self.payment_move_ids:
            if move.difference_management == 'mark_as_paid':
                self.env['account.move'].create_discount_entry(move.payment_difference,
                                                               move.destination_account_2_id.id, self.partner_id.id)

        return action
