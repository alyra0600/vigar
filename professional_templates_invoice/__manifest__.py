# -*- coding: utf-8 -*-
{
    "name": "Professional Report Templates Invoices",
    "license": "OPL-1",
    "support": "support@optima.co.ke",
    "summary": """
        Professional Report Templates: Purchase Order, RFQ, Sales Order,
        Quotation, Invoice, Delivery Note and Picking List""",
    "description": """
    Below are some of the main features (Full documentation coming soon):

    Covers Purchase Order, RFQ, Sales Order, Quotation, Delivery Note and Picking List

    5 different Report Templates to choose from for each report type mentioned above

    Upload high resolution company logo for each report

    Set the theme colors for your report to match your company colors

    You can set the text color for Company name in the report separately

    You can set the text color for Customer name in the report separately

    You can set the Background Color for odd and even lines (i.e quotation lines, order lines) in all the reports

    Line numbering for all lines (i.e quotation lines, order lines)

    You will be able to configure default  colors and theme settings for all reports (found in the company form) and also custom settings per report generated

    We can also do more customizations upon purchase (at minimal or no cost at all) depending on the feature you want
    """,
    "author": "Optima ICT Services LTD",
    "website": "http://www.optima.co.ke",
    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/odoo/addons/base/module/module_data.xml
    # for the full list
    "category": "Accounting & Finance",
    "images": ["static/description/main.png"],
    "version": "0.2.0",
    # any module necessary for this one to work correctly
    "depends": [
        "base",
        "account",
        "l10n_mx",
        "l10n_mx_edi",
        # "sale_management",
        # "purchase",
        # "stock",
        # "sale_stock",
        # "delivery",
    ],
    "external_dependencies": {"python": ["num2words", "PyPDF2"]},
    # always loaded
    "data": [
        "security/ir.model.access.csv",
        "views/res_company_view.xml",
        "views/res_config_view.xml",
        #"views/res_partner.xml",
        "views/company_footer.xml",
        "views/company_address.xml",
        "views/company_address_noname.xml",
        "views/category.xml",
        "views/report_style_views.xml",
        "views/ir_actions_report_xml.xml",
        "views/account_journal_views.xml",
        "reports/invoice_reports.xml",
        "invoice/invoice_lines.xml",
        "invoice/atm_template.xml",
        "invoice/switch_templates.xml",
        "invoice/dl_envelope.xml",
        "invoice/modern_template.xml",
        "invoice/classic_template.xml",
        "invoice/retro_template.xml",
        "invoice/tva_template.xml",
        "invoice/odoo_template.xml",
        "invoice/band_template.xml",
        "invoice/military_template.xml",
        "invoice/western_template.xml",
        "invoice/slim_template.xml",
        "invoice/cubic_template.xml",
        "invoice/clean_template.xml",
        "invoice/100miles_template.xml",
        "invoice/ascend_template.xml",
        "invoice/account_invoice_view.xml",
        #"data/res_currency_data.xml",
        "data/default_style.xml",
    ],
    "installable": True,
    "auto_install": False,
    "application": True,
}
