import base64
import logging
from datetime import datetime
from io import BytesIO

import xlsxwriter
from dateutil.relativedelta import relativedelta
from lxml import etree

from odoo import fields, models, tools
from odoo.exceptions import UserError
from odoo.tools import (
    DEFAULT_SERVER_DATE_FORMAT as DF,
    DEFAULT_SERVER_DATETIME_FORMAT as DTF,
)
from odoo.tools.translate import _

_logger = logging.getLogger(__name__)


class WizardImportElectronicDocument(models.TransientModel):
    _name = "wizard.import.electronic.document"
    _description = "Wizard to import documents from txt files"

    name = fields.Char(string="File name")
    file_content = fields.Binary("File to import", filters=None)
    file_note = fields.Binary("Notes")
    document_ids = fields.Char("Documents Imported")

    def _make_report_notes(self, message_list):
        fp = BytesIO()
        workbook = xlsxwriter.Workbook(fp, {"in_memory": True, "constant_memory": True})
        sheet_name = "Observations"
        worksheet = workbook.add_worksheet(sheet_name)
        format_bold = workbook.add_format({"bold": True, "text_wrap": True})
        format_merge_center = workbook.add_format(
            {"align": "center", "valign": "vcenter", "bold": True}
        )
        FIELDS_SHOW = [
            "message",
        ]
        COLUM_POS = {f: i for i, f in enumerate(FIELDS_SHOW)}
        COLUM_SIZE = {
            "message": 100,
        }
        COLUM_HEADER = {
            "message": "Observaciones",
        }
        COLUM_FORMAT = {
            "message": False,
        }
        current_row = 0
        worksheet.merge_range(
            current_row,
            0,
            current_row,
            max(COLUM_POS[FIELDS_SHOW[-1]], 1),
            _("OBSERVATIONS FOUND DURING THE IMPORT"),
            format_merge_center,
        )
        current_row += 1
        for key, value in list(COLUM_HEADER.items()):
            worksheet.write(current_row, COLUM_POS[key], value, format_bold)
        for line in message_list:
            current_row += 1
            for field_name, field_value in list(line.items()):
                if field_name not in FIELDS_SHOW:
                    continue
                worksheet.write(
                    current_row,
                    COLUM_POS[field_name],
                    field_value,
                    COLUM_FORMAT[field_name],
                )
        current_row += 1
        # ancho de columnas
        for column_name, position in list(COLUM_POS.items()):
            worksheet.set_column(position, position, COLUM_SIZE[column_name])
        workbook.close()
        fp.seek(0)
        data = fp.read()
        fp.close()
        return data

    def _get_file_content(self):
        util_model = self.env["l10n_ec.utils"]
        encoding = "ISO-8859-1"
        options = {"encoding": encoding, "field_delimiter": "\t"}
        file_data, errors = util_model.read_file(self.file_content, options)
        if len(file_data) <= 2:
            raise UserError(_("File does not has the expected structure"))
        header = file_data[0]
        header2 = file_data[1]
        detail = file_data[2:]
        file_lines = []
        for item, pos in enumerate(header):
            header[item] = pos.replace("\r", "")
        for item, pos in enumerate(header2):
            header2[item] = pos.replace("\r", "")
        values = {}
        for index, row in enumerate(detail):
            # los datos estan en la primer linea, pero el total siempre viene en una segunda linea
            # asi que se deben hacer 2 iteracciones para tener los datos completos
            # los numeros pares seran los datos
            # los numeros impares seran el total, que es cuando se completa los valores para crear 1 registro
            if index % 2 == 0:
                values = dict(list(zip(header, [x.strip() for x in row])))
            else:
                values.update(dict(list(zip(header2, [x.strip() for x in row]))))
                file_lines.append(values)
                values = {}
        return file_lines, errors

    def action_import(self):
        xml_data = self.env["sri.xml.data"]
        Documents = self.env["documents.document"].sudo()
        document_import_model = self.env["l10n_ec.electronic.document.imported"]
        documents_imported = document_import_model.browse()
        file_lines, errors = self._get_file_content()
        message_list = []
        message_list.extend([dict(message=msj) for msj in errors])
        values_to_create = []
        client_ws = xml_data.get_current_wsClient("2", "authorization")
        if not client_ws:
            raise UserError(_("Sorry, Cannot connect to SRI"))
        total_lines = len(file_lines)
        for nline, line in enumerate(file_lines):
            try:
                access_key = line.get("NUMERO_AUTORIZACION")
                if not access_key:
                    message_list.append(
                        {
                            "message": _(
                                "Error process line %s %s. NUMERO_AUTORIZACION is empty"
                            )
                            % (nline, line)
                        }
                    )
                    continue
                if document_import_model.search_count(
                    [("l10n_ec_xml_key", "=", access_key)]
                ):
                    message_list.append(
                        {
                            "message": "Error process line {}. {} already exist".format(
                                nline, access_key
                            )
                        }
                    )
                    continue
                _logger.info(
                    _("downloading xml file %s of %s with access key: %s"),
                    nline + 1,
                    total_lines,
                    access_key,
                )
                values = {
                    "l10n_ec_electronic_authorization": access_key,
                    "l10n_ec_xml_key": access_key,
                }
                xml_authorized = document_import_model._l10n_ec_download_file(
                    client_ws, access_key
                )
                if not xml_authorized:
                    message = _(
                        "Can not download file with access key: %s" % (access_key)
                    )
                    _logger.error(message)
                    message_list.append({"message": message})
                    continue
                file_xml = etree.fromstring(xml_authorized)
                is_company_valid = document_import_model._l10n_ec_is_xml_valid(file_xml)
                if not is_company_valid:
                    message = _(
                        "The xml file with access key: %s is badly formatted or not find a company"
                        % (access_key)
                    )
                    _logger.error(message)
                    message_list.append({"message": message})
                    continue
                values["company_id"] = is_company_valid.id
                values_to_create.append(values)
            except Exception as ex:
                message = _("Error process line %s. Error detail: %s") % (
                    line.get("NUMERO_AUTORIZACION", ""),
                    tools.ustr(ex),
                )
                _logger.error(message)
                message_list.append({"message": message})
        if values_to_create:
            documents_imported = document_import_model.create(values_to_create)
            total_lines = len(documents_imported)
            for nline, document in enumerate(documents_imported):
                try:
                    _logger.info(
                        _("Processing xml file %s of %s with access key: %s"),
                        nline + 1,
                        total_lines,
                        document.l10n_ec_xml_key,
                    )
                    document._action_download_file(client_ws)
                except Exception as ex:
                    message = _("Error validating xml files. Error detail: %s") % (
                        tools.ustr(ex)
                    )
                    _logger.error(message)
                    message_list.append({"message": message})
        document_tag_sri = self.env.ref(
            "l10n_ec_import_electronic_documents.documents_sri_tag", False
        )
        if document_tag_sri and documents_imported:
            file_name = self._get_file_name_for_save(
                documents_imported.mapped("company_id"),
                min(
                    documents_imported.filtered(
                        lambda x: x.l10n_ec_emision_date
                    ).mapped("l10n_ec_emision_date")
                ),
            )
            current_document = Documents.search(
                [
                    ("folder_id", "=", document_tag_sri.folder_id.id),
                    ("tag_ids", "=", document_tag_sri.id),
                    ("name", "=", file_name),
                ],
                limit=1,
            )
            if not current_document:
                attachment = self.env["ir.attachment"].create(
                    {
                        "name": file_name,
                        "datas": self.file_content,
                        "store_fname": file_name,
                        "description": file_name,
                    }
                )
                Documents.create(
                    {
                        "attachment_id": attachment.id,
                        "folder_id": document_tag_sri.folder_id.id,
                        "tag_ids": [(6, 0, document_tag_sri.ids)],
                        "name": file_name,
                    }
                )
        vals_to_write = {
            "name": False,
            "document_ids": documents_imported.ids or False,
        }
        if message_list:
            vals_to_write.update(
                {
                    "file_note": base64.encodebytes(
                        self._make_report_notes(message_list)
                    ),
                    "name": _("Documents not imported %s.xls")
                    % fields.Datetime.context_timestamp(self, datetime.now()).strftime(
                        DTF
                    ),
                }
            )
        self.write(vals_to_write)
        if not message_list:
            return self.action_open_document()
        form_view_id_xml = "l10n_ec_import_electronic_documents.wizard_import_electronic_document_resume_form_view"
        views = [(self.env.ref(form_view_id_xml).id, "form")]
        action_vals = {
            "name": _("Documents Imported"),
            "res_model": self._name,
            "views": views,
            "type": "ir.actions.act_window",
            "context": self._context,
            "view_type": "form",
            "res_id": self.id,
            "target": "new",
        }
        return action_vals

    def action_open_document(self):
        action_vals = {
            "name": _("Documents Imported"),
            "res_model": "l10n_ec.electronic.document.imported",
            "views": [[False, "tree"], [False, "form"]],
            "type": "ir.actions.act_window",
            "context": self._context,
        }
        if self.document_ids:
            document_ids = tools.safe_eval(self.document_ids)
            domain = [("id", "in", document_ids)]
            action_vals["domain"] = domain
            if len(document_ids) == 1:
                action_vals.update({"res_id": document_ids[0], "view_mode": "form"})
            else:
                action_vals["view_mode"] = "tree,form"
        return action_vals

    def _get_file_name_for_save(self, company, date_reference):
        date_reference = date_reference + relativedelta(day=1, days=-1, months=1)
        return (
            f"Documentos Electronicos {company.vat} {date_reference.strftime(DF)}.txt"
        )
