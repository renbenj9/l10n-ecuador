from odoo import fields, models


class AccountEdiDocument(models.Model):
    _inherit = "account.edi.document"

    l10n_ec_authorization_date = fields.Datetime(
        "Authorization Date", readonly=True, index=True
    )
    l10n_ec_authorization = fields.Char(
        "Authorization", size=49, readonly=True, index=True
    )
    l10n_ec_access_key = fields.Char(
        "Access Key", size=49, readonly=True, index=True, tracking=True
    )
