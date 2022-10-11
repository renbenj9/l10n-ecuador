from odoo import fields, models


class AccountEdiDocument(models.Model):
    _inherit = "account.edi.document"

    # company_id = fields.Many2one("res.company", string="Company",
    # default=lambda self: self.env.company)
    # partner_id = fields.Many2one("res.partner", "Customer", index=True, auto_join=True)

    number_document = fields.Char(
        "Document Number", compute="_compute_document_datas", store=True, index=True
    )

    l10n_ec_authorization_date = fields.Datetime(
        "Authorization Date", readonly=True, index=True
    )
    l10n_ec_access_key = fields.Char("Access Key", size=49, readonly=True, index=True)

    def _compute_document_datas(self):
        return "PENDIENTE DEFINIR"
