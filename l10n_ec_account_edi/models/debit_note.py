# -*- coding: utf-8 -*-

class DebitNote:

    def _l10n_ec_get_info_debit_note(self, account_edi_document, edi_date_format):
        account_edi_document.ensure_one()
        debit_note = account_edi_document.move_id
        company = debit_note.company_id or account_edi_document.env.company
        date_debit = debit_note.invoice_date
        taxes_data = debit_note._l10n_ec_get_taxes_grouped_by_tax_group()
        amount_total = abs(taxes_data.get("base_amount") + taxes_data.get("tax_amount"))

        debit_note_dict = {
            "fechaEmision": date_debit.strftime(edi_date_format),
            "dirEstablecimiento": account_edi_document._l10n_ec_clean_str(
                debit_note.journal_id.l10n_ec_emission_address_id.street or ""
            )[:300],
            "contribuyenteEspecial": company.l10n_ec_get_resolution_data(None),
            "obligadoContabilidad": account_edi_document._l10n_ec_get_required_accounting(
                company.partner_id.property_account_position_id
            ),
            # Customer data
            "tipoIdentificacionComprador": debit_note.l10n_ec_get_identification_type(),
            "razonSocialComprador": account_edi_document._l10n_ec_clean_str(
                debit_note.commercial_partner_id.name
            )[:300],
            "identificacionComprador": debit_note.commercial_partner_id.vat,
            # Debit Note data
            "codDocModificado": "01",
            "numDocModificado": debit_note.l10n_ec_legacy_document_number,
            "fechaEmisionDocSustento": debit_note.l10n_ec_legacy_document_date.strftime(
                edi_date_format
            ),
            "totalSinImpuestos": account_edi_document._l10n_ec_number_format(
                debit_note.amount_untaxed, 6
            ),
            "totalConImpuestos": account_edi_document.l10n_ec_header_get_total_with_taxes(taxes_data),
            "importeTotal": account_edi_document._l10n_ec_number_format(amount_total, 6),
            "pagos": debit_note._l10n_ec_get_payment_data(),
            "detalles": account_edi_document._l10n_ec_header_get_document_lines_edi_data(taxes_data),

            "infoAdicional": account_edi_document._l10n_ec_get_info_aditional(),
        }

        debit_note_dict.update(account_edi_document._l10n_ec_get_info_tributaria(debit_note))
        return debit_note_dict

