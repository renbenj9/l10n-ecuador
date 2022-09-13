from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class AccountJournal(models.Model):
    _inherit = "account.journal"

    bi_sequence_id = fields.Many2one(
        comodel_name="ir.sequence", string="Entry Sequence", copy=False
    )
    bi_sequence_next_number = fields.Integer(
        string="Next Sequence Number", copy=False, default=1
    )
    bi_refund_sequence_id = fields.Many2one(
        comodel_name="ir.sequence", string="Credit Note Entry Sequence", copy=False
    )
    bi_refund_sequence_next_number = fields.Integer(
        string="Credit Note Next Number", copy=False, default=1
    )

    @api.constrains("l10n_ec_entity", "l10n_ec_emission")
    def _constrains_l10n_ec_entity_emission(self):
        for rec in self:
            if rec.l10n_ec_entity:
                if len(rec.l10n_ec_entity) < 3 or not rec.l10n_ec_entity.isnumeric():
                    raise ValidationError(
                        _(
                            "Length less than 3 numbers or The point of entity "
                            "must contain only numbers"
                        )
                    )

            if rec.l10n_ec_emission:
                if (
                    len(rec.l10n_ec_emission) < 3
                    or not rec.l10n_ec_emission.isnumeric()
                ):
                    raise ValidationError(
                        _(
                            "Length less than 3 numbers or The point of "
                            "emission must contain only numbers"
                        )
                    )

    def write(self, vals):
        res = super(AccountJournal, self).write(vals)
        if "bi_sequence_next_number" in vals and self.type in ("sale", "purchase"):
            for rec in self:
                if rec.bi_sequence_id:
                    if (
                        rec.bi_sequence_id.use_date_range is True
                        and len(rec.bi_sequence_id.date_range_ids) >= 1
                    ):
                        for i in rec.bi_sequence_id.date_range_ids:
                            if i.date_from <= self.write_date.date() <= i.date_to:
                                i.sudo().write(
                                    {
                                        "number_next_actual": vals[
                                            "bi_sequence_next_number"
                                        ]
                                    }
                                )
                    else:
                        rec.bi_sequence_id.sudo().write(
                            {"number_next_actual": vals["bi_sequence_next_number"]}
                        )
        if "bi_refund_sequence_next_number" in vals and self.type in (
            "sale",
            "purchase",
        ):
            for rec in self:
                if rec.bi_sequence_id:
                    if (
                        rec.bi_refund_sequence_id.use_date_range is True
                        and len(rec.bi_refund_sequence_id.date_range_ids) >= 1
                    ):
                        for i in rec.bi_refund_sequence_id.date_range_ids:
                            if i.date_from <= self.write_date.date() <= i.date_to:
                                i.sudo().write(
                                    {
                                        "number_next_actual": vals[
                                            "bi_refund_sequence_next_number"
                                        ]
                                    }
                                )
                    else:
                        rec.bi_refund_sequence_id.sudo().write(
                            {
                                "number_next_actual": vals[
                                    "bi_refund_sequence_next_number"
                                ]
                            }
                        )
        return res
