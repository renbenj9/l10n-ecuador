import logging

from lxml import etree

from odoo import _, api, fields, models, tools

_logger = logging.getLogger(__name__)


class L10nEcWithhold(models.Model):
    _inherit = ["l10n_ec.xml.parser", "l10n_ec.withhold"]
    _name = "l10n_ec.withhold"

    l10n_ec_amount_imported = fields.Float(
        string="Amount Imported", readonly=True, copy=False
    )
    has_amount_diff = fields.Boolean(
        string="Has amount Differences?",
        compute="_compute_has_amount_difference",
        store=True,
    )

    @api.depends("line_ids.type", "line_ids.tax_amount", "l10n_ec_amount_imported")
    def _compute_has_amount_difference(self):
        for withholding in self:
            has_amount_diff = False
            if withholding.l10n_ec_amount_imported:
                has_amount_diff = (
                    withholding.currency_id.compare_amounts(
                        (withholding.tax_iva + withholding.tax_rent),
                        withholding.l10n_ec_amount_imported,
                    )
                    != 0
                )
            withholding.has_amount_diff = has_amount_diff

    @api.onchange("electronic_authorization")
    def _onchange_l10n_ec_electronic_authorization(self):
        warning = {}
        messages = []
        if (
            self.electronic_authorization
            and len(self.electronic_authorization) == 49
            and self.type == "sale"
        ):
            WithholdLineModel = self.env["l10n_ec.withhold.line"]
            xml_data = self.env["sri.xml.data"]
            xml_authorized = ""
            client_ws = xml_data.get_current_wsClient("2", "authorization")
            if not client_ws:
                _logger.error(
                    "Cannot connect to SRI to download Withholding file with access key %s",
                    self.electronic_authorization,
                )
                return
            try:
                xml_authorized = self.env[
                    "l10n_ec.electronic.document.imported"
                ]._l10n_ec_download_file(client_ws, self.electronic_authorization)
            except Exception as ex:
                _logger.error(tools.ustr(ex))
            if not xml_authorized:
                return
            withhold_xml = etree.fromstring(xml_authorized)
            document_list = self._l10n_ec_get_document_info_from_xml(withhold_xml)
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
                if document_info.tag == "comprobanteRetencion":
                    withholding_vals = self.with_context(
                        allowed_company_ids=company.ids
                    ).l10n_ec_xml_prepare_withholding_vals(company, document_info)
                    if withholding_vals:
                        xml_version = document_info.attrib.get("version") or "1.0"
                        self.update(withholding_vals)
                        l10n_ec_amount_imported = 0.0
                        self.line_ids = [(5, 0)]
                        if xml_version == "2.0.0":
                            info_lines = []
                            for sustento in document_info.docsSustento:
                                for line in sustento.docSustento.retenciones:
                                    for retention in line.retencion:
                                        info_lines.append(retention)
                        else:
                            info_lines = document_info.impuestos.impuesto
                        for detail_xml in info_lines:
                            (
                                percent_tax,
                                message_tax_list,
                            ) = self.l10n_ec_xml_find_tax_for_withholding(detail_xml)
                            messages.extend(message_tax_list)
                            vals_line = self.l10n_ec_xml_prepare_withholding_line_vals(
                                detail_xml, percent_tax
                            )
                            if withholding_vals.get("invoice_id"):
                                vals_line["invoice_id"] = withholding_vals["invoice_id"]
                            l10n_ec_amount_imported += (
                                vals_line.get("tax_amount") or 0.0
                            )
                            document_line = WithholdLineModel.new(vals_line)
                            vals_line = document_line._convert_to_write(
                                {
                                    name: document_line[name]
                                    for name in document_line._cache
                                }
                            )
                            self.line_ids |= document_line
                        self.l10n_ec_amount_imported = l10n_ec_amount_imported
        if messages:
            warning = {
                "title": _("Information for User"),
                "message": "\n".join(messages),
            }
        return {"warning": warning}
