from odoo import models


class AccountDebitNote(models.TransientModel):
    _inherit = 'account.debit.note'

    def _prepare_default_values(self, move):
        """ Recover invoice data for complete debit note to Ecuador. """
        res = super()._prepare_default_values(move)

        document = move.l10n_latam_document_number
        document_date = move.invoice_date
        document_authorization = move.l10n_ec_xml_access_key

        self.move_ids.l10n_ec_legacy_document_number = document
        self.move_ids.l10n_ec_legacy_document_date = document_date
        self.move_ids.l10n_ec_legacy_document_authorization = document_authorization

        return res
