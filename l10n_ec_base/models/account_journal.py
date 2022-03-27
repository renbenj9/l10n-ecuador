# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models


class AccountJournal(models.Model):
    _inherit = "account.journal"

    l10n_ec_sri_payment_id = fields.Many2one(
        "l10n_ec.sri.payment.method",
        "SRI Payment Method",
    )
    # similar to internal_type of l10n_latam.document.type
    # for domain's purpose on invoice view
    l10n_latam_internal_type = fields.Selection(
        [
            ("invoice", "Invoices"),
            ("debit_note", "Debit Notes"),
            ("credit_note", "Credit Notes"),
            ("liquidation", "Liquidation"),
        ],
        string="Use journal in",
    )

    @api.onchange("type")
    def _onchange_type(self):
        res = super(AccountJournal, self)._onchange_type()
        if self.type in ("sale", "purchase"):
            if not self.l10n_latam_internal_type:
                self.l10n_latam_internal_type = "invoice"
        else:
            self.l10n_latam_internal_type = False
        return res

    @api.model
    def _search(
        self,
        args,
        offset=0,
        limit=None,
        order=None,
        count=False,
        access_rights_uid=None,
    ):
        if self.env.context.get("l10n_latam_internal_type") and self.env.company.country_id.code == "EC":
            internal_type = self.env.context.get("l10n_latam_internal_type")
            if internal_type == "credit_note":
                args.append(("l10n_latam_internal_type", "in", ("invoice", internal_type)))
            elif internal_type in ("out_receipt", "in_receipt"):
                args.append(("l10n_latam_use_documents", "=", False))
            else:
                args.append(("l10n_latam_internal_type", "=", internal_type))
        return super(AccountJournal, self)._search(
            args,
            offset=offset,
            limit=limit,
            order=order,
            count=count,
            access_rights_uid=access_rights_uid,
        )
