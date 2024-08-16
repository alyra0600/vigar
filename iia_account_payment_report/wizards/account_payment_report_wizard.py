from odoo import api, fields, models
from dateutil.relativedelta import relativedelta
from datetime import datetime, timedelta
import math
import logging

_logger = logging.getLogger(__name__)

'''
    /*************************************************************************
    * Descripción
      Creación de informe de pagos.
    * VERSION
      1.0
    * Autor:
      Erick Enrique Abrego Gonzalez
    * Fecha:
      15/04/2024
    *************************************************************************/
'''


class AccountPaymentReportWizard(models.TransientModel):
    _name = 'account.payment.report.wizard'
    _description = 'Creador de informe de pagos'

    account_period = fields.Selection(string='Periodo contable', selection=[
        ('current_month', 'Este mes'),
        ('current_trimester', 'Este trimeste'),
        ('current_year', 'Este año financiero'),
        ('last_month', 'Último mes'),
        ('last_quarter', 'Último cuarto'),
        ('last_year', 'Último año fiscal'),
        ('custom', 'Perzonalizado')
    ], default='current_month')
    initial_date = fields.Date(string="Fecha inicial del periodo")
    end_date = fields.Date(string='Fecha final del periodo')
    company_id = fields.Many2one(comodel_name="res.company", string="Compañía", default=lambda self: self.env.company)
    report_type = fields.Selection(string="Tipo de reporte", selection=[('in','Ingreso'),('out','Egreso'),('both','General')], default="in")

    @api.onchange('account_period')
    def _calculate_initial_date(self):
        if self.account_period == 'current_month':
            self.initial_date = datetime.today().replace(day=1)
            self.end_date = self.initial_date + relativedelta(months=1) - timedelta(days=1)
        elif self.account_period == 'current_trimester':
            self.initial_date = datetime.today().replace(day=1) - relativedelta(months=2)
            self.end_date = self.initial_date + relativedelta(months=3) - timedelta(days=1)
        elif self.account_period == 'current_year':
            self.initial_date = datetime.today().replace(day=1, month=1)
            self.end_date = datetime.today().replace(day=31, month=12)
        elif self.account_period == 'last_month':
            self.initial_date = datetime.today().replace(day=1) - relativedelta(months=1)
            self.end_date = datetime.today().replace(day=1) - timedelta(days=1)
        elif self.account_period == 'last_quarter':
            initial_quarter = math.ceil(datetime.today().month / 3.)
            if initial_quarter == 1:
                self.initial_date = datetime.today().replace(day=1, month=10) - relativedelta(years=1)
                self.end_date = datetime.today().replace(day=31, month=12) - relativedelta(years=1)
            elif initial_quarter == 2:
                self.initial_date = datetime.today().replace(day=1, month=1)
                self.end_date = datetime.today().replace(day=31, month=3)
            elif initial_quarter == 3:
                self.initial_date = datetime.today().replace(day=1, month=4)
                self.end_date = datetime.today().replace(day=30, month=6)
            else:
                self.initial_date = datetime.today().replace(day=1, month=7)
                self.end_date = datetime.today().replace(day=30, month=9)
        elif self.account_period == 'last_year':
            self.initial_date = datetime.today().replace(day=1, month=1) - relativedelta(years=1)
            self.end_date = self.initial_date.replace(day=31, month=12)
        else:
            pass

    def _get_in_lines(self):
        invoice_in_query = f"""
            SELECT
                {self.id} as wizard_id,
                'in' AS report_type,
                partner.vat as rfc_receiver,
                partner.complete_name as nombre_partner,
                partner.company_registry as codigo_partner,
                company_partner.vat as rfc_emitter,
                estado.name as entidad_partner,
                vendedor.login as nombre_vendedor,
                equipo.name->>'es_MX' as equipo_ventas,
                am_debit.id AS invoice_id,
                am_debit.amount_totaL as invoice_amount,
                am_credit.id AS payment_id,
                am_debit.invoice_date,
                apr.max_date AS payment_date,
                am_credit.ref as memo_pago,
                am_debit.l10n_mx_edi_cfdi_uuid as folio_factura,
                am_credit.l10n_mx_edi_cfdi_uuid as folio_pago,
                am_credit.journal_id,
                am_credit.amount_total,
                am_credit.currency_id,
                am_credit.l10n_mx_edi_payment_method_id AS payment_method_id,
                apr.amount AS payment_amount
            FROM account_partial_reconcile apr
            JOIN account_move_line aml_debit ON aml_debit.id = apr.debit_move_id
            JOIN account_move am_debit ON am_debit.id = aml_debit.move_id
            JOIN account_move_line aml_credit ON aml_credit.id = apr.credit_move_id
            JOIN account_move am_credit ON am_credit.id = aml_credit.move_id
            JOIN res_partner partner on partner.id = am_debit.partner_id
            JOIN res_company company on company.id = am_debit.company_id
            JOIN res_partner company_partner on company_partner.id = company.partner_id
            JOIN res_country_state estado on partner.state_id = estado.id            
            JOIN res_users vendedor on vendedor.id = am_debit.invoice_user_id
            JOIN crm_team equipo on equipo.id = am_debit.team_id
            
            WHERE aml_credit.payment_id IS NOT null AND am_debit.move_type = 'out_invoice' AND apr.max_date BETWEEN '{self.initial_date}' 
                  AND '{self.end_date}' AND am_debit.company_id = {self.company_id.id} AND am_debit.state = 'posted'
            ORDER BY am_debit.name
        """
        self.env.cr.execute(invoice_in_query)
        invoice_in = self.env.cr.dictfetchall()
        invoice_in = self.get_tax_values(invoice_in)

        return invoice_in

    def _get_out_lines(self):
        invoice_out_query = f"""
            SELECT
                {self.id} as wizard_id,
                'out' AS report_type,
                partner.vat as rfc_emitter,
                partner.complete_name as nombre_partner,
                company_partner.vat as rfc_receiver,
                estado.name as entidad_partner,
                am_credit.id AS invoice_id,
                am_credit.amount_totaL as invoice_amount,
                am_debit.id AS payment_id,
                am_credit.invoice_date,
                apr.max_date AS payment_date,
                am_credit.l10n_mx_edi_cfdi_uuid as folio_factura,
                am_debit.l10n_mx_edi_cfdi_uuid as folio_pago,
                am_debit.journal_id,
                am_debit.amount_total,
                am_debit.currency_id,
                am_debit.l10n_mx_edi_payment_method_id AS payment_method_id,
                apr.amount AS payment_amount
            FROM account_partial_reconcile apr
            JOIN account_move_line aml_debit ON aml_debit.id = apr.debit_move_id
            JOIN account_move am_debit ON am_debit.id = aml_debit.move_id
            JOIN account_move_line aml_credit ON aml_credit.id = apr.credit_move_id
            JOIN account_move am_credit ON am_credit.id = aml_credit.move_id
            JOIN res_partner partner on partner.id = am_credit.partner_id
            JOIN res_company company on company.id = am_credit.company_id
            JOIN res_partner company_partner on company_partner.id = company.partner_id
            JOIN res_country_state estado on partner.state_id = estado.id            

            WHERE aml_debit.payment_id IS NOT null AND am_credit.move_type = 'in_invoice' AND apr.max_date BETWEEN '{self.initial_date}' 
                  AND '{self.end_date}' AND am_credit.company_id = {self.company_id.id} AND am_credit.state = 'posted'
            ORDER BY am_credit.name
        """
        self.env.cr.execute(invoice_out_query)
        invoice_in = self.env.cr.dictfetchall()
        invoice_in = self.get_tax_values(invoice_in)
        return invoice_in

    def get_tax_values(self, invoice_data):
        for i, move in enumerate(invoice_data):
            invoice_id = self.env["account.move"].browse(move["invoice_id"])
            iva = ieps = iva_ret = isr_ret = 0
            iva_reverse = ieps_reverse = iva_ret_reverse = isr_ret_reverse = 0
            amount_reverse = 0

            if invoice_id.tax_totals.get('groups_by_subtotal'):
                for tax in invoice_id.tax_totals.get('groups_by_subtotal')['Importe sin impuestos']:
                    if "IVA" in tax['tax_group_name'] and not "ret" in str(tax['tax_group_name']).lower():
                        iva += invoice_id.currency_id.round(tax['tax_group_amount'])
                    elif "IEPS" in tax['tax_group_name']:
                        ieps += invoice_id.currency_id.round(tax['tax_group_amount'])
                    elif "IVA" in tax['tax_group_name'] and "ret" in str(tax['tax_group_name']).lower():
                        iva_ret += invoice_id.currency_id.round(tax['tax_group_amount'])
                    elif "ISR" in tax['tax_group_name'] and "ret" in str(tax['tax_group_name']).lower():
                        isr_ret += invoice_id.currency_id.round(tax['tax_group_amount'])

            for reconciled_move in invoice_id.invoice_payments_widget["content"]:
                if not reconciled_move.get("account_payment_id"):
                    reverse_id = self.env["account.move"].sudo().browse(reconciled_move.get("move_id"))
                    amount_reverse +=reconciled_move.get("amount")
                    if reverse_id.tax_totals:
                        for tax in reverse_id.tax_totals.get('groups_by_subtotal')['Importe sin impuestos']:
                            if "IVA" in tax['tax_group_name'] and not "ret" in str(tax['tax_group_name']).lower():
                                iva_reverse += reverse_id.currency_id.round(tax['tax_group_amount'])
                            elif "IEPS" in tax['tax_group_name']:
                                ieps_reverse += reverse_id.currency_id.round(tax['tax_group_amount'])
                            elif "IVA" in tax['tax_group_name'] and "ret" in str(tax['tax_group_name']).lower():
                                iva_ret_reverse += reverse_id.currency_id.round(tax['tax_group_amount'])
                            elif "ISR" in tax['tax_group_name'] and "ret" in str(tax['tax_group_name']).lower():
                                isr_ret_reverse += reverse_id.currency_id.round(tax['tax_group_amount'])

            amount_total = invoice_id.amount_total - amount_reverse
            payment_percentage = abs(invoice_data[i]["payment_amount"] / amount_total) if amount_total > 0 else 0
            ieps = (ieps - ieps_reverse) * payment_percentage
            iva = (iva - iva_reverse) * payment_percentage
            iva_ret = (iva_ret - iva_ret_reverse)
            isr_ret = (isr_ret - isr_ret_reverse)
            invoice_data[i]["ieps_amount"] = ieps
            invoice_data[i]["iva_amount"] = iva
            invoice_data[i]["isr_ret_amount"] = isr_ret
            invoice_data[i]["iva_ret_amount"] = iva_ret
            invoice_data[i]["subtotal_payment"] = invoice_data[i]["payment_amount"] - ieps - iva - isr_ret - iva_ret
        return invoice_data

    def create_report(self):
        if self.report_type == 'in':
            data = self._get_in_lines()
        elif self.report_type == 'out':
            data = self._get_out_lines()
        else:
            data = self._get_in_lines() + self._get_out_lines()

        self.env["account.payment.report"].create(data)
        return {
            'name': "Reporte de pagos",
            'view_mode': "tree",
            'res_model': 'account.payment.report',
            'type': 'ir.actions.act_window',
            'domain': [('wizard_id','=', self.id)]
        }


