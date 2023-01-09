from odoo import fields, models


_TYPE_EXTRA_EC = [
    ("Impuestos", "Impuestos"),
    ("RetAir", "RetAir"),
    ("ImpExe", "ImpExe"),
    ("ImpGrav", "ImpGrav"),
    ("Imponible", "Imponible"),
    ("Reembolso", "Reembolso"),
    ("NoGraIva", "NoGraIva"),
    ("RetBien10", "RetBien10"),
    ("RetBienes", "RetBienes"),
    ("RetIva", "RetIva"),
    ("RetServ100", "RetServ100"),
    ("RetServ20", "RetServ20"),
    ("RetServ50", "RetServ50"),
    ("RetServicios", "RetServicios"),
    ("ISD", "ISD"),
    ("RetRenta", "RetRenta"),
]


class AccountTaxReport(models.Model):
    _inherit = "account.tax.report"

    l10n_ec_tax_form = fields.Char("SRI Tax Form", size=3)


class AccountTaxGroup(models.Model):
    _inherit = "account.tax.group"

    l10n_ec_xml_fe_code = fields.Char("Tax Code for Electronic Documents", size=5)
    l10n_ec_type = fields.Selection(
        selection_add=_TYPE_EXTRA_EC,
    )


class AccountTax(models.Model):
    _inherit = "account.tax"

    l10n_ec_xml_fe_code = fields.Char(
        "Tax Code for Electronic Documents",
        size=10,
        help="Tax Code used into xml files for electronic documents sent to S.R.I., "
        "If field is empty, description field are used instead",
    )
    l10n_ec_tax_support_id = fields.Many2one(
        "l10n_ec.sri.tax.support", string="Tax Support"
    )

    def get_data_from_tag(self, is_refund, tax_form="", field=""):
        repartition = "base"
        if self.tax_group_id.l10n_ec_type in [
            "RetBien10",
            "RetServ20",
            "RetServ50",
            "RetBienes",
            "RetServicios",
            "RetServ100",
            "RetIva",
        ]:
            repartition = "tax"
        tax_repartition_lines = (
            is_refund
            and self.refund_repartition_line_ids
            or self.invoice_repartition_line_ids
        ).filtered(lambda x: x.repartition_type == repartition)
        for tag in tax_repartition_lines.mapped("tag_ids").filtered(
            lambda x: x.tax_report_line_ids.report_id.l10n_ec_tax_form
        ):
            try:
                field = tag.name[1:].split("(")[0].strip()
            except Exception:
                pass
            tax_form = tag.tax_report_line_ids.report_id.l10n_ec_tax_form
        return tax_form, field


class AccountTaxTemplate(models.Model):
    _inherit = "account.tax.template"

    l10n_ec_xml_fe_code = fields.Char(
        "Tax Code for Electronic Documents",
        size=10,
        help="Tax Code used into xml files for electronic documents sent to S.R.I., "
        "If field is empty, description field are used instead",
    )
    l10n_ec_tax_support_id = fields.Many2one(
        "l10n_ec.sri.tax.support", string="Tax Support"
    )

    def _l10n_ec_get_tax_vals(self):
        # funcion generica para devolver datos adicionales de impuestos
        # para ser llamada al momento de cargar el plan contable
        # o desde la instalacion del modulo(se ejecuta desde un post_init)
        return {
            "l10n_ec_xml_fe_code": self.l10n_ec_xml_fe_code,
            "l10n_ec_tax_support_id": self.l10n_ec_tax_support_id
            and self.l10n_ec_tax_support_id.id
            or False,
        }

    def _get_tax_vals(self, company, tax_template_to_tax):
        """This method generates a dictionnary of all the values for the tax that
        will be created."""
        self.ensure_one()
        val = super(AccountTaxTemplate, self)._get_tax_vals(
            company, tax_template_to_tax
        )
        val.update(self._l10n_ec_get_tax_vals())
        return val
