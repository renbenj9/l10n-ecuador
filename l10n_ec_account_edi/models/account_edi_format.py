from odoo import models
from odoo.odoo.exceptions import UserError
from odoo.tools.translate import _

FORMAT_CODES = ["ublec_1_0"]


class AccountEdiFormat(models.Model):
    _inherit = "account.edi.format"

    ####################################################
    # Export
    ####################################################

    def _get_xml_builder(self, company):
        # the EDI option will only appear on the journal of ecuadorian companies
        # ublec_1_0 new code format edi
        if self.code == "ublec_1_0" and company.country_id.code == "EC":
            return self.env["account.edi.xml.ubl_ec"]

    def _is_ubl_cii_available(self, company):
        """
        Returns a boolean indicating whether it is possible to generate an xml file using one
        of the formats from this module or not
        """
        return self._get_xml_builder(company) is not None

    ####################################################
    # Export: Account.edi.format override
    ####################################################

    def _is_required_for_invoice(self, invoice):
        # TO OVERRIDE
        self.ensure_one()
        if self.code not in FORMAT_CODES:
            return super()._is_required_for_invoice(invoice)

        return self._is_ubl_cii_available(invoice.company_id) and invoice.move_type in (
            "out_invoice",
            "out_refund",
        )

    def _is_compatible_with_journal(self, journal):
        # EXTENDS account_edi
        self.ensure_one()
        if self.code not in FORMAT_CODES:
            return super()._is_compatible_with_journal(journal)
        return self._is_ubl_cii_available(journal.company_id) and journal.type == "sale"

    def _post_invoice_edi(self, invoices):
        # EXTENDS account_edi
        self.ensure_one()

        if self.code not in FORMAT_CODES:
            return super()._post_invoice_edi(invoices)

        res = {}
        for invoice in invoices:
            builder = self._get_xml_builder(invoice.company_id)
            # For now, the errors are not displayed anywhere, don't want to annoy the user
            xml_content, errors = builder._export_invoice(invoice)

            attachment_create_vals = {
                "name": builder._export_invoice_filename(invoice),
                "raw": xml_content,
                "mimetype": "application/xml",
            }

            attachment_create_vals.update(
                {"res_id": invoice.id, "res_model": "account.move"}
            )

            attachment = self.env["ir.attachment"].create(attachment_create_vals)
            # avanzar

            # YRO 1. Add flow signature
            # YRO 1.1 Get valid electronic signature
            key_type_record = self.env["sri.key.type"].search(
                [("state", "=", "valid")], limit=1
            )
            # YRO 1.2 Send xml data for sing
            xml_signed = key_type_record.action_sign(xml_content)
            if not xml_signed:
                # TODO ponerlo en ingles
                raise UserError(
                    _(
                        "No se pudo firmar el documento, "
                        "por favor verifique configuracion de firma electronica este correcta"
                    )
                )
            # YRO 2  Send xml sing to SRI
            # 3 proces response sri

            res[invoice] = {
                "success": True,
                "attachment": attachment,
            }

        return res
