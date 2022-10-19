
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"


    l10n_ec_max_intentos = fields.Integer("Maximum attempts for authorization")
    l10n_ec_type_environment = fields.Selection(
        [
            ("test", "Test"),
            ("production", "Production"),
        ],
        string="Environment  type for electronic documents",
        default="test",
    )
