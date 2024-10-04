# -*- encoding: utf-8 -*-
{
    'name': 'Boveda fiscal EE',
    'summary': """
        Importacion de documentos fiscales desde el SAT.
    """,
    'description': """
        Importacion de documentos fiscales
          -Facturas
          -Pagos
          -Nóminas
          -Carta porte
    """,
    'author': 'Integra Informatica',
    'website': "integrainformatica.mx",
    'category': 'Accounting & Finance',
    'version': '17.18',
    'depends': ['account', 'l10n_mx_edi', 'purchase'],
    'data': [
        'security/res_groups.xml',
        'security/ir.model.access.csv',
        'security/ir_rule.xml',
        
        'data/ir_actions_server.xml',
        'data/ir_cron.xml',
        
        'wizard/purchase_order_wizard_view.xml',
        'views/cfdi_view.xml',
        'views/account_account.xml',
        'views/account_cfdi_payment_tax.xml',
        'views/account_journal.xml',
        'views/account_move_view.xml',
        'views/cfdi_concepto_view.xml',
        'views/esignature_view.xml',
        'views/res_company_view.xml',
        'views/res_config_settings_view.xml',
        'views/res_partner_view.xml',
        'views/account_payment.xml',
        
        'wizard/account_move_cfdi_view.xml',
        'wizard/attach_xmls_wizard_view.xml',
        'wizard/cfdi_account_move_link_view.xml',
        'wizard/cfdi_xlsx_link.xml',
        'wizard/check_sat_status_cfdi_view.xml',
        'wizard/import_sat_view.xml',
        'wizard/import_zip_view.xml',
        'wizard/xml_invoice_reconcile_view.xml',
        
        'reports/cfdi_boveda_report.xml',
    ],
    'license': 'AGPL-3'
}

