from odoo import api, fields, models
from odoo.exceptions import ValidationError
import base64
import xlrd
import io

class CFDIXlsxLink(models.TransientModel):
    _name = 'cfdi.xlsx.link'
    _description = 'Relación Excel -> CFDI'

    file_data = fields.Binary(string="Adjunto")
    file_name = fields.Char(string="Nombre del adjunto")
    company_id = fields.Many2one(comodel_name="res.company", string="Empresa", default=lambda self: self.env.company)

    def read_xlsx(self):
        self = self.with_user(1)
        data = base64.decodebytes(self.file_data)
        report_file = io.BytesIO(data)
        xlsx = xlrd.open_workbook(file_contents=report_file.read())
        sheet = xlsx.sheet_by_index(0)
        columns = sheet.row_values(0)
        uuid_column = columns.index("UUID")
        due_column = columns.index("SALDO")
        amount_column = columns.index("IMPORTE")
        payment_journal_column = columns.index(("DIARIO PAGO"))
        invoice_journal_column = columns.index("DIARIO FACTURA")

        for row in range(sheet.nrows):
            if row == 0:
                continue
            uuid = sheet.cell_value(row, uuid_column)
            due_amount = sheet.cell_value(row, due_column)
            amount = sheet.cell_value(row, amount_column)
            payment_journal = sheet.cell_value(row, payment_journal_column)
            invoice_journal = sheet.cell_value(row, invoice_journal_column)

            payment_journal_id = self.get_journal_id(payment_journal)
            invoice_journal_id = self.get_journal_id(invoice_journal)

            cfdi_id = self.env["iia_boveda_fiscal.cfdi"].sudo().search([("uuid","=",uuid),("move_id","=",False)], limit=1)
            if cfdi_id:
                if not cfdi_id.partner_id_receptor or not cfdi_id.partner_id_emisor:
                    cfdi_id.set_partner_cfdi()
                if cfdi_id.partner_id_emisor and cfdi_id.partner_id_receptor:
                    cfdi_id.journal_id = invoice_journal_id.id
                    cfdi_id.set_concept_tax_ids()
                    if not cfdi_id.move_id:
                        cfdi_id.action_done()
                    invoice_id = cfdi_id.move_id
                    invoice_id.sudo().write({
                        "name": str(cfdi_id.serie or "") + str(cfdi_id.folio or "") if cfdi_id.folio or cfdi_id.serie else invoice_id.name
                    })
                    if due_amount != amount:
                        self.create_initial_payment(invoice_id, due_amount, amount, payment_journal_id)

    def create_initial_payment(self, invoice_id, due_amount, amount, journal_id):
        payment_register_obj = self.env["account.payment.register"]
        if journal_id:
            data = {
                "journal_id": journal_id.id,
                "amount": amount - due_amount,
                "communication": invoice_id.name
            }
            payment_id = payment_register_obj.sudo().with_context(active_model="account.move.line", active_ids=invoice_id.line_ids.ids).create(data)
            payment_id.action_create_payments()
        else:
            raise ValidationError("Es necesario asignar un diario para saldo inicial, favor de validar.")


    def get_journal_id(self, journal_name):
        journal_id = self.env["account.journal"].sudo().search([("company_id.id","=",self.company_id.id),("name","=",journal_name)],limit=1)
        if not journal_id:
            raise ValidationError(f"No fue posible encontrar un diario contable con el nombre {journal_name} en la empresa {self.company_id.name}, favor de validar.")
        return journal_id