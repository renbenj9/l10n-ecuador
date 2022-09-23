from odoo import models


class AccountEdiFormat(models.Model):
    _name = "account.edi.format"

    def _is_required_for_invoice(self, invoice):
        """Indicate if this EDI must be generated for the invoice passed as parameter.

        :param invoice: An account.move having the invoice type.
        :returns:       True if the EDI must be generated, False otherwise.
        """
        # TO OVERRIDE
        self.ensure_one()
        return True

    def _is_compatible_with_journal(self, journal):
        """Indicate if the EDI format should appear on the journal passed as parameter
            to be selected by the user.
        If True, this EDI format will appear on the journal.

        :param journal: The journal.
        :returns:       True if this format can appear on the journal, False otherwise.
        """
        # TO OVERRIDE
        self.ensure_one()
        return journal.type == "sale"

    def _post_invoice_edi(self, invoices):
        """Create the file content representing the invoice (and calls web services if
         necessary).

        :param invoices:    A list of invoices to post.
        :returns:  A dictionary with the invoice as key and as value, another dictionary:
        * success: True if the edi was successfully posted.
        * attachment: The attachment representing the invoice in this edi_format.
        * error:  An error if the edi was not successfully posted.
        * blocking_level: (optional) How bad is the error (how should the edi flow be blocked ?)
        """
        # TO OVERRIDE
        self.ensure_one()
        return {}
