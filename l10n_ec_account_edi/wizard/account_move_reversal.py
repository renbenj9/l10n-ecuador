# -*- coding: utf-8 -*-
from odoo import models, fields, api

class AccountMoveReversal(models.TransientModel):
    _inherit = "account.move.reversal"

    def _prepare_default_reversal(self, move):
        res = super()._prepare_default_reversal(move)
        move.update({"l10n_ec_reason": self.reason})
        return res


