import re

from odoo import _, api, models
from odoo.exceptions import ValidationError


class AccountJournal(models.Model):
    _inherit = "account.journal"

    @api.constrains('l10n_ec_entity', 'l10n_ec_emission')
    def _constrains_l10n_ec_entity_emission(self):
        for rec in self:
            if rec.l10n_ec_entity:
                if re.match(r"^[a-zA-Z][ a-zA-Z]*", rec.l10n_ec_entity):
                    raise ValidationError(_("The point of entity must contain only numbers"))

            if rec.l10n_ec_emission:
                if re.match(r"^[a-zA-Z][ a-zA-Z]*", rec.l10n_ec_emission):
                    raise ValidationError(_("The point of emission must contain only numbers"))
