# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'l10_ec_base',
    'version': '1.1',
    'summary': 'Invoices & Payments',
    'sequence': 10,
    'author': "Renan Nazate , Hernan Espinoza",
    'description': """
Invoicing & Payments
====================
The specific and easy-to-use Invoicing system in Odoo allows you to keep track of your accounting, even when you are not an accountant. It provides an easy way to follow up on your vendors and customers.

You could use this simplified accounting in case you work with an (external) account to keep your books, and you still want to keep track of payments. This module also offers you an easy method of registering payments, without having to encode complete abstracts of account.
    """,
    'category': 'Accounting/Localizations/Account Charts',
    'depends': [
        "base",
        "base_iban",
        "account_debit_note",
        "l10n_latam_invoice_document",
        "l10n_latam_base",
    ],
    'data': [
        # Chart of Accounts
        "data/account_chart_template_data.xml",
        "data/account_group_template_data.xml",
        "data/account.account.template.csv",
        "data/account_chart_template_setup_accounts.xml",
        # Taxes
        "data/account_tax_group_data.xml",
        "data/account_tax_report_data.xml",
        "data/account_tax_template_vat_data.xml",
        "data/account_tax_template_withhold_profit_data.xml",
        "data/account_tax_template_withhold_vat_data.xml",
        "data/account_fiscal_position_template.xml",
        # Partners data
        "data/res.bank.csv",
        "data/l10n_latam_identification_type_data.xml",
        "data/res_partner_data.xml",
        # Other data
        "data/account_chart_template_configure_data.xml",
        "data/l10n_latam.document.type.csv",
        "data/l10n_ec.sri.payment.csv",
        "views/account_tax_view.xml",
        "views/l10n_latam_document_type_view.xml",
        "views/l10n_ec_sri_payment.xml",
        # "views/account_journal_view.xml",
        "security/ir.model.access.csv",
    ],
    'installable': True,
    'application': True,
    'auto_install': True,
    'post_init_hook': '_account_post_init',
    'license': 'LGPL-3',
}
