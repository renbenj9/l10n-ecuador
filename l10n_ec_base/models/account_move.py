#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging

from odoo import _, fields, models


_logger = logging.getLogger(__name__)

BASES_IMPONIBLES = ["ImpExe", "ImpGrav", "Imponible", "Reembolso", "NoGraIva"]

RET_COMPRAS = [
    "RetAir",
    "RetIva",
    "RetBien10",
    "RetBienes",
    "RetServ50",
    "RetServ100",
    "RetServ20",
    "RetServicios",
]


class AccountMove(models.Model):
    _inherit = "account.move"

    sri_ats_line_ids = fields.One2many(
        "l10n_ec.sri.ats.line", inverse_name="invoice_id", string=_("ATS Line")
    )

    sri_tax_line_ids = fields.One2many(
        "l10n_ec.sri.tax.line", inverse_name="invoice_id", string=_("SRI Taxes")
    )

    def get_sri_tax_lines(self):
        for inv in self:
            tax_lines = {}
            sri_tax_lines = []
            for line in inv.invoice_line_ids.sorted(lambda x: x.price_subtotal):
                if line.sri_tax_line_ids:
                    line.sri_tax_line_ids.unlink()
                for taxline in line.tax_ids:
                    for tax in taxline:
                        if line not in tax_lines:
                            tax_lines.update({line: {}})
                        price_unit = line.price_unit * (
                            1 - (line.discount or 0.0) / 100.0
                        )
                        is_refund = (tax.type_tax_use == "sale" and price_unit < 0) or (
                            tax.type_tax_use == "purchase" and price_unit > 0
                        )
                        tax_form, field = tax.get_data_from_tag(is_refund)
                        if tax_form and field:
                            if tax_form not in tax_lines[line]:
                                tax_lines[line].update({tax_form: {}})
                            if field not in tax_lines[line][tax_form]:
                                tax_lines[line][tax_form].update({field: {}})
                            tax_data = tax.json_friendly_compute_all(
                                price_unit,
                                currency_id=line.company_currency_id
                                and line.company_currency_id.id
                                or False,
                                quantity=line.quantity,
                                product_id=line.product_id
                                and line.product_id.id
                                or False,
                                partner_id=inv.partner_id
                                and line.partner_id.id
                                or False,
                            )
                            base = amount = 0
                            for td in tax_data.get("taxes", []):
                                base += td.get("base")
                                amount += td.get("amount")
                            if tax.tax_group_id.l10n_ec_type in [
                                "RetBien10",
                                "RetServ20",
                                "RetServ50",
                                "RetBienes",
                                "RetServicios",
                                "RetServ100",
                                "RetIva",
                            ]:
                                tax_repartition_lines = (
                                    is_refund
                                    and tax.refund_repartition_line_ids
                                    or tax.invoice_repartition_line_ids
                                ).filtered(lambda x: x.repartition_type == "tax")
                                base = (
                                    price_unit
                                    * line.quantity
                                    * tax_repartition_lines.factor
                                )
                            tax_lines[line][tax_form][field].update(
                                {
                                    "group": tax.tax_group_id
                                    and tax.tax_group_id.id
                                    or False,
                                    "percent": abs(tax.amount) or 0.0,
                                    "percent_code": tax.l10n_ec_xml_fe_code
                                    or field
                                    or 0,
                                    "tax": field,
                                    "tax_code": tax.tax_group_id
                                    and tax.tax_group_id.l10n_ec_xml_fe_code
                                    or field,
                                    "amount": abs(amount) or 0.00,
                                    "base": abs(base),
                                }
                            )
            if tax_lines:
                for line, form_vals in tax_lines.items():
                    for form, field_vals in form_vals.items():
                        for field, vals in field_vals.items():
                            base_vals = {
                                "invoice_line_id": line.id,
                                "tax_form": form,
                                "field": field,
                            }
                            sri_tax_lines.append({**base_vals, **vals})
            return sri_tax_lines

    def consolidate_sri_tax_lines(self):
        """
        Crea un consolidado de impuestos en la factura para
        permitir la revisión de impuestos por parte del contador.
        :return:
        """
        for inv in self:
            # Limpiamos las líneas de impuestos previamente creados.
            inv.sri_tax_line_ids.unlink()

            sri_tax_lines = []

            lines = self.invoice_line_ids.mapped("sri_tax_line_ids")
            for line in lines:
                tax_line = next(
                    (
                        item
                        for item in sri_tax_lines
                        if item["tax_form"] == line.tax_form
                        and item["field"] == line.field
                    ),
                    False,
                )

                if not tax_line:
                    sri_tax_lines.append(
                        {
                            "invoice_id": inv.id,
                            "tax_form": line.tax_form,
                            "field": line.field,
                            "group": line.group and line.group.id or False,
                            "amount": abs(line.amount),
                            "base": line.base,
                            "percent": line.percent,
                            "tax": line.tax,
                            "tax_code": line.tax_code,
                            "percent_code": line.percent_code,
                        }
                    )
                else:
                    tax_line["amount"] += abs(line.amount)
                    tax_line["base"] += abs(line.base)

            for tax in sri_tax_lines:
                self.env["l10n_ec.sri.tax.line"].create(tax)
        return True

    def get_sri_ats_lines(self):
        for inv in self:
            # Limpia líneas de ATS anteriormente calculadas
            inv.sri_ats_line_ids.unlink()

            # Hacemos una lista de los sustentos de la factura.
            sustentos = inv.invoice_line_ids.mapped(
                "tax_ids.l10n_ec_tax_support_id.code"
            )

            if not sustentos and inv.move_type in ["out_invoice", "out_refund"]:
                # Utilizamos 'NA' para generar líneas del ATS en ventas.
                sustentos = ["NA"]

            # Diccionario para crear la línea de ATS en la factura.
            sri_ats_lines = []

            for s in sustentos:
                basenograiva = 0.0
                baseimponible = 0.0
                baseimpgrav = 0.0
                baseimpexe = 0.0
                montoice = 0.0
                montoiva = 0.0
                valretbien10 = 0.0
                valretserv20 = 0.0
                valretserv50 = 0.0
                valorretbienes = 0.0
                valorretservicios = 0.0
                valretserv100 = 0.0
                valorretiva = 0.0
                valorretrenta = 0.0

                detalleair = []
                impuestos = []

                for line in inv.invoice_line_ids:
                    codsustento = line.mapped(
                        "tax_ids.l10n_ec_tax_support_id.code"
                    ) or ["NA"]
                    if codsustento and codsustento[0] == s:
                        for tl in line.sri_tax_line_ids:
                            # AGREGAMOS LAS BASES DE IMPUESTO SEGÚN CORRESPONDE.
                            if tl.group.l10n_ec_type == "NoGraIva":
                                basenograiva += tl.base
                            elif tl.group.l10n_ec_type == "Imponible":
                                baseimponible += tl.base
                            elif tl.group.l10n_ec_type == "ImpGrav":
                                baseimpgrav += tl.base
                                # Solamente el grupo ImpGrav genera valores en montoiva
                                montoiva += tl.amount
                            elif tl.group.l10n_ec_type == "ImpExe":
                                baseimpexe += tl.base
                            # RETENCIONES DE COMPRAS.
                            elif tl.group.l10n_ec_type == "RetBien10":
                                valretbien10 += tl.amount
                            elif tl.group.l10n_ec_type == "RetServ20":
                                valretserv20 += tl.amount
                            elif tl.group.l10n_ec_type == "RetServ50":
                                valretserv50 += tl.amount
                            elif tl.group.l10n_ec_type == "RetBienes":
                                valorretbienes += tl.amount
                            elif tl.group.l10n_ec_type == "RetServicios":
                                valorretservicios += tl.amount
                            elif tl.group.l10n_ec_type == "RetServ100":
                                valretserv100 += tl.amount
                            # RETENCIONES EN VENTAS.
                            elif tl.group.l10n_ec_type == "RetIva":
                                valorretiva += tl.amount
                            elif tl.group.l10n_ec_type == "RetRenta":
                                valorretrenta += tl.amount
                            # AGREGAMOS EL VALOR DEL ICE.
                            elif tl.group.l10n_ec_type == "Ice":
                                montoice += tl.amount

                            # HACEMOS LOS DICCIONARIOS DE RETENCIONES DE IR.
                            if tl.group.l10n_ec_type in RET_COMPRAS:
                                # Buscamos una línea de retención con el mismo código.
                                air = next(
                                    (
                                        item
                                        for item in detalleair
                                        if item["codretair"] == tl.tax
                                    ),
                                    False,
                                )

                                if not air:
                                    # Agregamos el diccionario, no se agrega directamente con 0,0 porque
                                    # al hacerlo, falla la búsqueda anterior.
                                    detalleair.append(
                                        {
                                            "group": tl.group and tl.group.id or False,
                                            "codigo": tl.tax_code,
                                            "valretair": abs(tl.amount),
                                            "baseimpair": tl.base,
                                            "codretair": tl.percent_code,
                                            "porcentajeair": tl.percent or 0,
                                        }
                                    )
                                else:
                                    air["baseimpair"] += tl.base
                                    air["valretair"] += abs(tl.amount)

                            # IMPUESTOS PARA RETENCION ATS
                            if tl.group.l10n_ec_type in [
                                "Imponible",
                                "ImpGrav",
                                "NoGraIva",
                            ]:
                                # Buscamos una línea de retención con el mismo código.
                                imps = next(
                                    (
                                        imp
                                        for imp in impuestos
                                        if imp["percent_code"] == tl.percent_code
                                        and imp["codimpuestodocsustento"] == tl.tax_code
                                    ),
                                    False,
                                )

                                if not imps:
                                    # Agregamos el diccionario, no se agrega directamente con 0,0 porque
                                    # al hacerlo, falla la búsqueda anterior.
                                    impuestos.append(
                                        {
                                            "codimpuestodocsustento": tl.tax_code,
                                            "codigoporcentaje": tl.percent_code,
                                            "baseimponible": tl.base,
                                            "tarifa": tl.percent,
                                            "valorimpuesto": tl.amount,
                                        }
                                    )
                                else:
                                    imps["baseimponible"] += tl.base
                                    imps["valorimpuesto"] += abs(tl.amount)

                # Agregamos 0,0 a la lista para que Flectra cree las líneas, no poner 0,0 directamente.
                detalleair_line = []
                for air in detalleair:
                    detalleair_line.append((0, 0, air))

                impuesto_line = []
                for imp in impuestos:
                    impuesto_line.append((0, 0, imp))

                sri_ats_lines.append(
                    {
                        "invoice_id": inv.id,
                        "codsustento": "{:0>2}".format(s),
                        "basenograiva": abs(basenograiva),
                        "baseimponible": abs(baseimponible),
                        "baseimpgrav": abs(baseimpgrav),
                        "baseimpexe": abs(baseimpexe),
                        "montoice": abs(montoice),
                        "montoiva": abs(montoiva),
                        "valretbien10": abs(valretbien10),
                        "valretserv20": abs(valretserv20),
                        "valretserv50": abs(valretserv50),
                        "valorretbienes": abs(valorretbienes),
                        "valorretservicios": abs(valorretservicios),
                        "valretserv100": abs(valretserv100),
                        "valorretiva": abs(valorretiva),
                        "valorretrenta": abs(valorretrenta),
                        "impuestos_ids": impuesto_line,
                        "retenciones_ids": detalleair_line,
                    }
                )

            for l in sri_ats_lines:
                self.env["l10n_ec.sri.ats.line"].create(l)
        return True

    def get_sri_cero_iva(self):
        """
        Si la linea no tiene retención de IVA creamos un impuesto con
        IVA 0% para el xml de retenciones de venta en facturación electrónica.
        No se requiere en compras.
        """
        # TODO: permitir elegir el impuesto por defecto en la configuración de la compañía.
        for inv in self:
            for line in inv.invoice_line_ids:
                base = sum(
                    t.base
                    for t in line.sri_tax_line_ids
                    if t.group.l10n_ec_type == "RetAir"
                )
                residual = line.price_subtotal - base
                if round(residual, 2) > 0:
                    self.env["l10n_ec.sri.tax.line"].create(
                        {
                            "invoice_line_id": line.id,
                            "tax_form": "NA",
                            "field": "NA",
                            "group": self.env.ref("l10n_ec.tax_group_withhold_vat").id,
                            "amount": 0.0,
                            "base": residual,
                            "percent": "0",
                            "tax": "RET. IVA 0%",
                            "tax_code": "2",
                            "percent_code": "7",
                        }
                    )
        return True

    def get_sri_cero_air(self):
        """
        En caso de haber valores no declarados en el formulario 103
        Creamos un impuesto en el campo 332 por retención 0% general.
        :return:
        """
        # TODO: permitir elegir el impuesto por defecto en la configuración de la compañía.
        for row in self:
            if row.l10n_latam_document_type_id.code == "05":
                return True
            for line in row.invoice_line_ids:

                # Agregamos el 332 solo si hay una base imponible.
                if not any(
                    tax.tax_group_id.l10n_ec_type in BASES_IMPONIBLES
                    for tax in line.tax_ids
                ):
                    continue

                # La base es la diferencia entre las bases existentes
                # y el subtotal para cubrir casos como el 322.
                base = sum(
                    t.base
                    for t in line.sri_tax_line_ids
                    if t.group.l10n_ec_type == "RetAir"
                )
                residual = line.price_subtotal - base
                if round(residual, 2) > 0:
                    self.env["l10n_ec.sri.tax.line"].create(
                        {
                            "invoice_line_id": line.id,
                            "tax_form": "103",
                            "field": "332",
                            "group": self.env.ref("l10n_ec_base.tax_group_ret_ir").id,
                            "amount": 0.0,
                            "base": residual,
                            "percent": "0",
                            "tax": "332",
                            "tax_code": "1",
                            "percent_code": "332",
                        }
                    )
        return True

    def button_prepare_sri_declaration(self):
        for row in self:
            # Genera las lineas de impuestos y ats en compras y ventas.
            for line in row.get_sri_tax_lines():
                self.env["l10n_ec.sri.tax.line"].create(line)

            # Aplicar solo en compras.
            # Antes de get_sri_ats_lines y consolidate_sri_tax_lines.
            # TODO revisar si es necesario esto en notas de credito
            if row.move_type == "in_invoice":
                row.get_sri_cero_air()

            # Aplicar solo en ventas.
            if row.move_type in ("out_refund", "out_invoice"):
                row.get_sri_cero_iva()

            # Consolida las lineas de impuestos en compras y ventas.
            row.consolidate_sri_tax_lines()

            # Se debe ejecutar luego de las anteriores para tener todos los impuestos.
            row.get_sri_ats_lines()
        return True

    def action_post(self):
        res = super().action_post()
        for row in self:
            if row.move_type not in ["entry", "out_receipt", "in_receipt"]:
                row.button_prepare_sri_declaration()
        return res


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    sri_tax_line_ids = fields.One2many(
        "l10n_ec.sri.tax.line", inverse_name="invoice_line_id", string="SRI Taxes"
    )


class SriTaxLine(models.Model):
    """SRI tax line"""

    _name = "l10n_ec.sri.tax.line"
    _description = __doc__
    _order = "tax_form,field"

    invoice_line_id = fields.Many2one(
        "account.move.line",
        ondelete="cascade",
        string="Invoice line",
    )
    invoice_id = fields.Many2one(
        "account.move",
        ondelete="cascade",
        string="Invoice",
    )
    tax_form = fields.Char(
        "Tax Form",
    )
    field = fields.Char(
        "Campo",
    )
    group = fields.Many2one("account.tax.group")
    base = fields.Float(
        "Tax Basis",
        digits="Product Price",
    )
    amount = fields.Float(
        "Tax Amount",
        digits="Product Price",
    )
    percent = fields.Char(
        "Percent",
    )
    percent_code = fields.Char(
        "Percent Code",
    )
    tax = fields.Char(
        "Tax code (Forms)",
    )
    tax_code = fields.Char(
        "Tax Code (EDI)",
    )


class SriAtsLine(models.Model):
    _name = "l10n_ec.sri.ats.line"
    _order = "codsustento"

    invoice_id = fields.Many2one(
        "account.move",
        ondelete="cascade",
        string="Invoice",
        required=False,
        domain=[("move_type", "not in", ["entry", "out_receipt", "in_receipt"])],
    )
    codsustento = fields.Char("codSustento")
    basenograiva = fields.Float("baseNoGraIva", digits="Product Price")
    baseimponible = fields.Float("baseImponible", digits="Product Price")
    baseimpgrav = fields.Float("baseImpGrav", digits="Product Price")
    baseimpexe = fields.Float("baseImpExe", digits="Product Price")
    montoice = fields.Float("montoIce", digits="Product Price")
    montoiva = fields.Float("montoIva", digits="Product Price")
    # Purchane withholdings.
    valretbien10 = fields.Float("valRetBien10", digits="Product Price")
    valretserv20 = fields.Float("valRetServ20", digits="Product Price")
    valretserv50 = fields.Float("valRetServ50", digits="Product Price")
    valorretbienes = fields.Float("valorRetBienes", digits="Product Price")
    valorretservicios = fields.Float("valorRetServicios", digits="Product Price")
    valretserv100 = fields.Float("valRetServ100", digits="Product Price")
    # Sale withholdings.
    valorretiva = fields.Float("valorRetIva", digits="Product Price")
    valorretrenta = fields.Float("valorRetRenta", digits="Product Price")
    impuestos_ids = fields.One2many(
        "l10n_ec.sri.taxes",
        string="Impuestos",
        inverse_name="ats_line_id",
    )
    retenciones_ids = fields.One2many(
        "l10n_ec.sri.withholdings", string="Retenciones", inverse_name="ats_line_id"
    )


class SriTaxDetails(models.Model):
    """SRI Taxes"""

    _name = "l10n_ec.sri.taxes"
    _description = __doc__

    ats_line_id = fields.Many2one(
        "l10n_ec.sri.ats.line", ondelete="cascade", string="ATS Line"
    )
    codimpuestodocsustento = fields.Char("codImpuestoDocSustento")
    codigoporcentaje = fields.Char("codigoPorcentaje")
    baseimponible = fields.Float("baseImponible", digits="Product Price")
    tarifa = fields.Float("tarifa")
    valorimpuesto = fields.Float("valorImpuesto", digits="Product Price")


class SriWithholdingsDetails(models.Model):
    """SRI Withholdings"""

    _name = "l10n_ec.sri.withholdings"
    _description = __doc__
    _order = "codretair"

    ats_line_id = fields.Many2one(
        "l10n_ec.sri.ats.line", ondelete="cascade", string="ATS Line"
    )
    group = fields.Many2one("account.tax.group")
    codigo = fields.Char("codigo")
    codretair = fields.Char("codRetAir")
    baseimpair = fields.Float("baseImpAir", digits="Product Price")
    porcentajeair = fields.Float("porcentajeAir")
    valretair = fields.Float("valRetAir", digits="Product Price")
