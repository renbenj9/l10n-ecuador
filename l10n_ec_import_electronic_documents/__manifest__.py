{
    "name": "Import Electronic Documents",
    "summary": """""",
    "description": """
    """,
    "author": "Spearhead",
    "website": "https://github.com/OCA/l10n-ecuador",
    "license": "LGPL-3",
    "category": "Account",
    "version": "13.0.0.0.1",
    "depends": ["account", "account_facturx", "l10n_ec_niif", "documents"],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "data/documents_sri_data.xml",
        "data/cron_jobs.xml",
        "data/action_server_data.xml",
        "wizard/wizard_import_electronic_document_view.xml",
        "views/l10n_ec_electronic_document_imported_view.xml",
        "views/withhold_view.xml",
        "views/res_config_view.xml",
    ],
}
