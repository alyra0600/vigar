# -*- coding: utf-8 -*-
{
    'name': "Reporte de facturas pagadas",
    'summary': """
        Reporte de auditoria para obtener la información de las facturas pagadas.
    """,
    'description': """
        Reporte de auditoria para obtener la información de las facturas pagadas.
    """,
    'author': "Erick Abrego",
    'website': "https://github.com/erickabrego",
    'category': 'Contabilidad',
    'version': '17.1',
    'depends': ['base','account','l10n_mx_edi'],
    'data': [
        'security/ir.model.access.csv',
        'views/account_payment_report.xml',
        'wizards/account_payment_report_wizard.xml'
    ],
    'license': 'AGPL-3'
}
