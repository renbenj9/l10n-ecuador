from odoo import models


class AccountWithholding(models.TransientModel):
    _inherit = "account.move"

    def _prepare_default_values(self, move):
        """Recover invoice data for withholdings to Ecuador"""
        res = super()._prepare_default_values(move)
        
        self.ensure_one()
        invoice = self.move_id
        type_invoice = invoice.move_type
        date_invoice = invoice.invoice_date
        company = invoice.company_id or self.env.company
        taxes_data = invoice._l10n_ec_get_taxes_grouped_by_tax_group()
        amount_total = abs(taxes_data.get("base_amount") + taxes_data.get("tax_amount"))
        currency = invoice.currency_id
        currency_name = currency.name or "DOLAR"
        
        if type_invoice == "out_invoice":
            withholding_data = {
            "fechaEmision": (date_invoice).strftime(EDI_DATE_FORMAT),
            "dirEstablecimiento": self._l10n_ec_clean_str(
                invoice.journal_id.l10n_ec_emission_address_id.street or ""
            )[:300],
            "contribuyenteEspecial": company.l10n_ec_get_resolution_data(date_invoice),
            "obligadoContabilidad": self._l10n_ec_get_required_accounting(
                company.partner_id.property_account_position_id
            )

            }
   
        

        return res
