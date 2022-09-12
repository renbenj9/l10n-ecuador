import re

from odoo import _, api, models
from odoo.exceptions import ValidationError


class AccountJournal(models.Model):
    _inherit = "account.journal"

    # ("^.+\\@(\\[?)[a-zA-Z0-9\\-\\.]+\\.([a-zA-Z]{2,3}|[0-9]{1,3})(\\]?)$", rec.email)

    @api.constrains('l10n_ec_entity', 'l10n_ec_emission')
    def _constrains_l10n_ec_entity_emission(self):
        for rec in self:
            if rec.l10n_ec_entity:
                if len(rec.l10n_ec_entity) < 3 or re.match(r"^[.*+\-?\\^${}()|[\]]", rec.l10n_ec_entity) \
                    or re.match(r"^[a-zA-Z][ a-zA-Z]*", rec.l10n_ec_entity):
                    raise ValidationError(_("Length less than 3 numbers or The point of entity must contain only numbers"))

            if rec.l10n_ec_emission:
                if len(rec.l10n_ec_emission) < 3 or re.match(r"^[.*+\-?\\^${}()|[\]]", rec.l10n_ec_emission) \
                    or re.match(r"^[a-zA-Z][ a-zA-Z]*", rec.l10n_ec_emission):
                    raise ValidationError(_("Length less than 3 numbers or The point of emission must contain only numbers"))
