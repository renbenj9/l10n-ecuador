import re

from odoo import _, api, models, fields
from odoo.exceptions import ValidationError


class AccountJournal(models.Model):
    _inherit = "account.journal"

    @api.constrains('l10n_ec_entity', 'l10n_ec_emission')
    def _constrains_l10n_ec_entity_emission(self):
        for rec in self:
            if rec.l10n_ec_entity:
                if len(rec.l10n_ec_entity) < 3 or not rec.l10n_ec_entity.isnumeric():
                    raise ValidationError(_("Length less than 3 numbers or The point of entity must contain only numbers"))

            if rec.l10n_ec_emission:
                if len(rec.l10n_ec_emission) < 3 or not rec.l10n_ec_emission.isnumeric():
                    raise ValidationError(_("Length less than 3 numbers or The point of emission must contain only numbers"))
