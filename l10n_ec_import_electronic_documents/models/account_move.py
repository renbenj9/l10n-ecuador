import logging
from datetime import datetime

from lxml import etree

from odoo import _, api, models, tools
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = ["l10n_ec.xml.parser", "account.move"]
    _name = "account.move"

    @api.onchange("l10n_ec_electronic_authorization")
    def _onchange_l10n_ec_electronic_authorization(self):
        warning = {}
        messages = []
        if (
            self.l10n_ec_electronic_authorization
            and len(self.l10n_ec_electronic_authorization) == 49
            and self.is_purchase_document()
            and self.company_id.l10n_ec_check_data_document_automatic
        ):
            xml_data = self.env["sri.xml.data"]
            xml_authorized = ""
            client_ws = xml_data.get_current_wsClient("2", "authorization")
            if not client_ws:
                _logger.error(
                    "Cannot connect to SRI to download file with access key %s",
                    self.l10n_ec_electronic_authorization,
                )
                return
            try:
                xml_authorized = self.env[
                    "l10n_ec.electronic.document.imported"
                ]._l10n_ec_download_file(
                    client_ws, self.l10n_ec_electronic_authorization
                )
            except Exception as ex:
                _logger.error(tools.ustr(ex))
            if not xml_authorized:
                return
            invoice_xml = etree.fromstring(xml_authorized)
            document_list = self._l10n_ec_get_document_info_from_xml(invoice_xml)
            for document_info in document_list:
                company = self._l10n_ec_get_company_for_xml(document_info)
                if not company:
                    messages.append(
                        _("Can't find company for current xml file, please review")
                    )
                    continue
                elif company != self.company_id:
                    messages.append(
                        _(
                            "file does not belong to the current company, please import file into company: %s"
                        )
                        % (company.name)
                    )
                    continue
                if document_info.tag == "factura":
                    if self.type != "in_invoice":
                        messages.append(
                            _(
                                "Electronic Authorization is for Invoice, but current document is not same type, "
                                "please create document on appropriated menu"
                            )
                        )
                        continue
                    messages, new_document = self.with_context(
                        allowed_company_ids=company.ids
                    )._l10n_ec_create_invoice_from_xml(document_info)
                elif document_info.tag == "notaCredito":
                    if self.type != "in_refund":
                        messages.append(
                            _(
                                "Electronic Authorization is for Credit Note, but current document is not same type, "
                                "please create document on appropriated menu"
                            )
                        )
                        continue
                    messages, new_document = self.with_context(
                        allowed_company_ids=company.ids, internal_type="credit_note"
                    )._l10n_ec_create_credit_note_from_xml(document_info)
                elif document_info.tag == "notaDebito":
                    if self.type != "in_invoice":
                        messages.append(
                            _(
                                "Electronic Authorization is for Debit Note, but current document is not same type, "
                                "please create document on appropriated menu"
                            )
                        )
                        continue
                    messages, new_document = self.with_context(
                        allowed_company_ids=company.ids, internal_type="debit_note"
                    )._l10n_ec_create_debit_note_from_xml(document_info)
        if messages:
            warning = {
                "title": _("Information for User"),
                "message": "\n".join(messages),
            }
        return {"warning": warning}

    @api.model
    def _l10n_ec_detect_xml(self, tree, file_name):
        # Quick check the tree looks like an xml authorized file.
        flag = self._l10n_ec_is_xml_valid(tree)
        error = None
        return {"flag": flag, "error": error}

    @api.model
    def _l10n_ec_decode_xml(self, invoice_xml):
        messages = []
        document_list = self._l10n_ec_get_document_info_from_xml(invoice_xml)
        for document_info in document_list:
            company = self._l10n_ec_get_company_for_xml(document_info)
            if not company:
                raise UserError(
                    _("Can't find company for current xml file, please review")
                )
            elif company != self.env.company:
                raise UserError(
                    _(
                        "file does not belong to the current company, please import file into company: %s"
                    )
                    % (company.name)
                )
            if document_info.tag == "factura":
                messages, new_document = self.with_context(
                    allowed_company_ids=company.ids
                )._l10n_ec_create_invoice_from_xml(document_info)
            elif document_info.tag == "notaCredito":
                messages, new_document = self.with_context(
                    allowed_company_ids=company.ids, internal_type="credit_note"
                )._l10n_ec_create_credit_note_from_xml(document_info)
            elif document_info.tag == "notaDebito":
                messages, new_document = self.with_context(
                    allowed_company_ids=company.ids, internal_type="debit_note"
                )._l10n_ec_create_debit_note_from_xml(document_info)
        if messages:
            # TODO: crear log de errores
            pass
        return self

    @api.model
    def _get_xml_decoders(self):
        # Override
        l10n_ec_decoders = [
            (
                "l10n_ec_electronic_xml",
                self._l10n_ec_detect_xml,
                self._l10n_ec_decode_xml,
            )
        ]
        return super(AccountMove, self)._get_xml_decoders() + l10n_ec_decoders

    def _l10n_ec_create_invoice_from_xml(self, document_info):
        InvoiceLineModel = self.env["account.move.line"]
        sri_util_model = self.env["l10n_ec.utils"]
        is_onchange_invoice = isinstance(self.id, models.NewId)
        company = self.env.company
        create_product = company.l10n_ec_import_create_product
        invoice_type = "in_invoice"
        document_code = document_info.infoTributaria.codDoc.text
        messages = []
        latam_document_type = self.l10n_latam_document_type_id
        if not latam_document_type:
            latam_document_type = self.l10n_ec_xml_get_latam_document_type(
                company, document_code
            )
        if not latam_document_type:
            messages.append(
                _("Cannot find Document type with code: %s") % document_code
            )
        vals_invoice = self.l10n_ec_xml_prepare_invoice_vals(
            company, document_info, latam_document_type, invoice_type
        )
        vals_invoice.update(
            {
                "invoice_date": datetime.strptime(
                    document_info.infoFactura.fechaEmision.text,
                    sri_util_model.get_formato_date(),
                ),
            }
        )
        domain_invoice = self.l10n_ec_xml_get_domain_for_invoice(vals_invoice)
        current_invoice = self.search(domain_invoice, limit=1)
        if current_invoice:
            messages.append(
                f"Ya existe una factura con el numero: {current_invoice.l10n_ec_get_document_number()} para el proveedor: {current_invoice.partner_id.name}, no se creo otro documento"
            )
            return messages, current_invoice
        if is_onchange_invoice:
            self.invoice_line_ids = [(5, 0)]
            self.line_ids = [(5, 0)]
            self.update(vals_invoice)
        else:
            self.write(vals_invoice)
        # provocar el onchange del partner
        self._onchange_partner_id()
        invoice_line_vals = []
        for detail_xml in document_info.detalles.detalle:
            supplier_taxes, message_tax_list = self.l10n_ec_xml_find_taxes(
                company, detail_xml
            )
            messages.extend(message_tax_list)
            product, message_product_list = self.l10n_ec_xml_find_create_product(
                detail_xml,
                supplier_taxes,
                vals_invoice["partner_id"],
                force_create_product=create_product,
            )
            messages.extend(message_product_list)
            vals_line = self.l10n_ec_xml_prepare_invoice_line_vals(
                detail_xml, product, supplier_taxes
            )
            invoice_line = InvoiceLineModel.new(vals_line)
            invoice_line._onchange_product_id()
            invoice_line.price_unit = vals_line["price_unit"]
            invoice_line.quantity = vals_line["quantity"]
            if vals_line.get("discount"):
                invoice_line.discount = vals_line["discount"]
            if supplier_taxes:
                invoice_line.tax_ids |= supplier_taxes
            if not invoice_line.account_id:
                invoice_line._get_computed_account()
            if not invoice_line.account_id:
                invoice_line.account_id = self.journal_id.default_debit_account_id
            if is_onchange_invoice:
                self.invoice_line_ids |= invoice_line
            else:
                vals_line_create = invoice_line._convert_to_write(
                    {name: invoice_line[name] for name in invoice_line._cache}
                )
                invoice_line_vals.append((0, 0, vals_line_create))
        if is_onchange_invoice:
            self.invoice_line_ids._onchange_price_subtotal()
            self._recompute_dynamic_lines(recompute_all_taxes=True)
        else:
            amount_total_imported = float(document_info.infoFactura.importeTotal.text)
            self.write({"invoice_line_ids": invoice_line_vals})
            decimal_places = self.currency_id.decimal_places
            if (
                tools.float_compare(
                    self.amount_total,
                    amount_total_imported,
                    precision_digits=decimal_places,
                )
                != 0
            ):
                messages.append(
                    f"Los totales no coinciden, Total sistema: {tools.float_repr(self.amount_total, decimal_places)}, "
                    f"total importado: {tools.float_repr(amount_total_imported, decimal_places)}. "
                    f"Documento: {vals_invoice['l10n_latam_document_number']}"
                )
        return messages, self

    @api.model
    def _l10n_ec_create_credit_note_from_xml(self, document_info):
        InvoiceLineModel = self.env["account.move.line"]
        sri_util_model = self.env["l10n_ec.utils"]
        is_onchange_invoice = isinstance(self.id, models.NewId)
        company = self.env.company
        create_product = company.l10n_ec_import_create_product
        invoice_type = "in_refund"
        document_code = document_info.infoTributaria.codDoc.text
        messages = []
        latam_document_type = self.l10n_latam_document_type_id
        if not latam_document_type:
            latam_document_type = self.l10n_ec_xml_get_latam_document_type(
                company, document_code
            )
        if not latam_document_type:
            messages.append(
                f"No se encontro un tipo de documento valido con codigo {document_code}"
            )
        vals_invoice = self.l10n_ec_xml_prepare_credit_note_vals(
            company, document_info, latam_document_type, invoice_type
        )
        vals_invoice.update(
            {
                "invoice_date": datetime.strptime(
                    document_info.infoNotaCredito.fechaEmision.text,
                    sri_util_model.get_formato_date(),
                ),
            }
        )
        domain_invoice = self.l10n_ec_xml_get_domain_for_invoice(vals_invoice)
        current_invoice = self.search(domain_invoice, limit=1)
        if current_invoice:
            messages.append(
                f"Ya existe una Nota de credito con el numero: {current_invoice.l10n_ec_get_document_number()} para el proveedor: {current_invoice.partner_id.name}, no se creo otro documento"
            )
            return messages, current_invoice
        if is_onchange_invoice:
            self.invoice_line_ids = [(5, 0)]
            self.line_ids = [(5, 0)]
            self.update(vals_invoice)
        else:
            self.write(vals_invoice)
        # provocar el onchange del partner
        self._onchange_partner_id()
        invoice_line_vals = []
        for detail_xml in document_info.detalles.detalle:
            supplier_taxes, message_tax_list = self.l10n_ec_xml_find_taxes(
                company, detail_xml
            )
            messages.extend(message_tax_list)
            product, message_product_list = self.l10n_ec_xml_find_create_product(
                detail_xml,
                supplier_taxes,
                vals_invoice["partner_id"],
                force_create_product=create_product,
            )
            messages.extend(message_product_list)
            vals_line = self.l10n_ec_xml_prepare_invoice_line_vals(
                detail_xml, product, supplier_taxes
            )
            invoice_line = InvoiceLineModel.new(vals_line)
            invoice_line._onchange_product_id()
            invoice_line.price_unit = vals_line["price_unit"]
            invoice_line.quantity = vals_line["quantity"]
            if vals_line.get("discount"):
                invoice_line.discount = vals_line["discount"]
            if supplier_taxes:
                invoice_line.tax_ids |= supplier_taxes
            if not invoice_line.account_id:
                invoice_line._get_computed_account()
            if not invoice_line.account_id:
                invoice_line.account_id = self.journal_id.default_debit_account_id
            if is_onchange_invoice:
                self.invoice_line_ids |= invoice_line
            else:
                vals_line_create = invoice_line._convert_to_write(
                    {name: invoice_line[name] for name in invoice_line._cache}
                )
                invoice_line_vals.append((0, 0, vals_line_create))
        if is_onchange_invoice:
            self.invoice_line_ids._onchange_price_subtotal()
            self._recompute_dynamic_lines(recompute_all_taxes=True)
        else:
            amount_total_imported = float(
                document_info.infoNotaCredito.valorModificacion.text
            )
            self.write({"invoice_line_ids": invoice_line_vals})
            decimal_places = self.currency_id.decimal_places
            if (
                tools.float_compare(
                    self.amount_total,
                    amount_total_imported,
                    precision_digits=decimal_places,
                )
                != 0
            ):
                messages.append(
                    f"Los totales no coinciden, Total sistema: {tools.float_repr(self.amount_total, decimal_places)}, "
                    f"total importado: {tools.float_repr(amount_total_imported, decimal_places)}. "
                    f"Documento: {vals_invoice['l10n_latam_document_number']}"
                )
        return messages, self

    @api.model
    def _l10n_ec_create_debit_note_from_xml(self, document_info):
        InvoiceLineModel = self.env["account.move.line"]
        sri_util_model = self.env["l10n_ec.utils"]
        is_onchange_invoice = isinstance(self.id, models.NewId)
        company = self.env.company
        create_product = company.l10n_ec_import_create_product
        invoice_type = "in_invoice"
        document_code = document_info.infoTributaria.codDoc.text
        messages = []
        latam_document_type = self.l10n_latam_document_type_id
        if not latam_document_type:
            latam_document_type = self.l10n_ec_xml_get_latam_document_type(
                company, document_code
            )
        if not latam_document_type:
            messages.append(
                f"No se encontro un tipo de documento valido con codigo {document_code}"
            )
        vals_invoice = self.l10n_ec_xml_prepare_debit_note_vals(
            company, document_info, latam_document_type, invoice_type
        )
        vals_invoice.update(
            {
                "invoice_date": datetime.strptime(
                    document_info.infoNotaDebito.fechaEmision.text,
                    sri_util_model.get_formato_date(),
                ),
            }
        )
        domain_invoice = self.l10n_ec_xml_get_domain_for_invoice(vals_invoice)
        current_invoice = self.search(domain_invoice, limit=1)
        if current_invoice:
            messages.append(
                f"Ya existe una Nota de debito con el numero: {current_invoice.l10n_ec_get_document_number()} para el proveedor: {current_invoice.partner_id.name}, no se creo otro documento"
            )
            return messages, current_invoice
        if is_onchange_invoice:
            self.invoice_line_ids = [(5, 0)]
            self.line_ids = [(5, 0)]
            self.update(vals_invoice)
        else:
            self.write(vals_invoice)
        # provocar el onchange del partner
        self._onchange_partner_id()
        invoice_line_vals = []
        for detail_xml in document_info.motivos.motivo:
            # tomar los impuestos del nodo principal y no del motivo
            supplier_taxes, message_tax_list = self.l10n_ec_xml_find_taxes(
                company, document_info.infoNotaDebito
            )
            messages.extend(message_tax_list)
            product, message_product_list = self.l10n_ec_xml_find_create_product(
                detail_xml,
                supplier_taxes,
                vals_invoice["partner_id"],
                force_create_product=create_product,
            )
            messages.extend(message_product_list)
            vals_line = self.l10n_ec_xml_prepare_debit_note_line_vals(
                detail_xml, product, supplier_taxes
            )
            invoice_line = InvoiceLineModel.new(vals_line)
            invoice_line._onchange_product_id()
            invoice_line.price_unit = vals_line["price_unit"]
            invoice_line.quantity = vals_line["quantity"]
            if vals_line.get("discount"):
                invoice_line.discount = vals_line["discount"]
            if supplier_taxes:
                invoice_line.tax_ids |= supplier_taxes
            if not invoice_line.account_id:
                invoice_line._get_computed_account()
            if not invoice_line.account_id:
                invoice_line.account_id = self.journal_id.default_debit_account_id
            if is_onchange_invoice:
                self.invoice_line_ids |= invoice_line
            else:
                vals_line_create = invoice_line._convert_to_write(
                    {name: invoice_line[name] for name in invoice_line._cache}
                )
                invoice_line_vals.append((0, 0, vals_line_create))
        if is_onchange_invoice:
            self.invoice_line_ids._onchange_price_subtotal()
            self._recompute_dynamic_lines(recompute_all_taxes=True)
        else:
            amount_total_imported = float(document_info.infoNotaDebito.valorTotal.text)
            self.write({"invoice_line_ids": invoice_line_vals})
            decimal_places = self.currency_id.decimal_places
            if (
                tools.float_compare(
                    self.amount_total,
                    amount_total_imported,
                    precision_digits=decimal_places,
                )
                != 0
            ):
                messages.append(
                    f"Los totales no coinciden, Total sistema: {tools.float_repr(self.amount_total, decimal_places)}, "
                    f"total importado: {tools.float_repr(amount_total_imported, decimal_places)}. "
                    f"Documento: {vals_invoice['l10n_latam_document_number']}"
                )
        return messages, self
