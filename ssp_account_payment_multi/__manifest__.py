# -*- coding: utf-8 -*-
# Copyright 2021 SystemSolutions.pro. - Ing Henry Vivas
{
    "name": "Multiple and Partial Invoice Payment",
    "version": "17.0.1.1.0",
    "description": """
        Multiple Pay or Pay Partial for Invoice Document Customer and Vendor.
    """,
    'price': 35,
    'currency': 'EUR',
    'license': 'OPL-1',
    'author' : "Odoo { Devs }",
    'sequence': 30,
    'email': 'controlwebmanger@gmail.com',
    'website':'http://OdooDevs.pro/',
    'live_test_url': 'https://demo17.OdooDevs.pro/',
    'category':"Accounting",
    'summary':"Using this module you can pay complete or partial pay multiple invoice payment in one click.",
    "depends": [
          "account","l10n_mx_edi"
    ],
    'data': [
        'security/ir.model.access.csv',
        'static/src/xml/security_groups.xml',
        'views/account_payment_view.xml',
        'views/invoice_list_view_inherit.xml',
        # 'views/res_user_view_form.xml',
        'views/action_open_payment_wizard.xml',
        'wizard/account_payment_register_view.xml',

    ],
    "images": ['static/description/main_screenshot.png'],
    'installable': True,
    'auto_install': False,
    'assets': {
        'web.assets_backend': [
            'ssp_account_payment_multi/static/src/js/account_payment_multi_field.js',
            # 'ssp_account_payment_multi/static/src/js/button_in_tree.js',
            'ssp_account_payment_multi/static/src/xml/account_payment.xml',
            # 'ssp_account_payment_multi/static/src/xml/list_view_button.xml',

        ],
        'web.assets_qweb': [
            'ssp_account_payment_multi/static/src/xml/account_payment.xml',
        ],
    },
}
