# -*- coding: utf-8 -*-
##############################################################################
##############################################################################

{
    'name': 'Customer Credit Limit',
    'version': '17.1',
    'sequence': 1,
    'category': 'Generic Modules/Accounting',
    'description':
        """
        """,
    'summary': 'Customer Credit Limit, Partner Credit Limit, Credit Limit, Sale limit,Customer Credit balance, Customer credit management, Sale credit approval, Sale customer credit approval, Sale Customer Credit Informatation,Credit approval,sale approval, credit workflow',
    'author': 'German Ponce & Devintelle',
    'website': 'http://poncesoft.blogspot.com',
    'depends': ['sale_management', 'account'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'wizard/customer_limit_wizard_view.xml',
        'views/partner_view.xml',
        'views/sale_order_view.xml',
        'views/parameter.xml',
    ],
    'demo': [],
    'images': ['images/main_screenshot.png'],
    'test': [],
    'css': [],
    'qweb': [],
    'js': [],
    'installable': True,
    'application': True,
    'auto_install': False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
