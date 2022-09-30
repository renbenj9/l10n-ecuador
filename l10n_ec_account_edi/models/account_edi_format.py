from odoo import models

from odoo.addons.account_edi_ubl_cii.models.account_edi_common import COUNTRY_EAS

FORMAT_CODES = [
    "facturx_1_0_05",
    "ubl_bis3",
    "ubl_de",
    "nlcius_1",
    "efff_1",
    "ubl_2_1",
    "ehf_3",
]


class AccountEdiFormat(models.Model):
    _inherit = "account.edi.format"

    ####################################################
    # Export
    ####################################################

    def _get_xml_builder(self, company):
        if self.code == "facturx_1_0_05":
            return self.env["account.edi.xml.cii"]
        # if the company's country is not in the EAS mapping, nothing is generated
        if self.code == "ubl_bis3" and company.country_id.code in COUNTRY_EAS:
            return self.env["account.edi.xml.ubl_bis3"]
        # the EDI option will only appear on the journal of dutch companies
        if self.code == "nlcius_1" and company.country_id.code == "NL":
            return self.env["account.edi.xml.ubl_nl"]
        # the EDI option will only appear on the journal of german companies
        if self.code == "ubl_de" and company.country_id.code == "DE":
            return self.env["account.edi.xml.ubl_de"]
        # the EDI option will only appear on the journal of belgian companies
        if self.code == "efff_1" and company.country_id.code == "BE":
            return self.env["account.edi.xml.ubl_efff"]

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
            if self.code not in ["facturx_1_0_05", "efff_1", "nlcius_1"]:
                attachment_create_vals.update(
                    {"res_id": invoice.id, "res_model": "account.move"}
                )

            attachment = self.env["ir.attachment"].create(attachment_create_vals)
            res[invoice] = {
                "success": True,
                "attachment": attachment,
            }

        return res
