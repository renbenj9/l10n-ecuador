# -*- coding: utf-8 -*-

from odoo import api, fields, models, _

class AccountMove(models.Model):
    _inherit = "account.move"

    def _get_ec_formatted_sequence(self, number=0):
        if number < 2:
            number = self.journal_id.sequence_init
        return super(AccountMove, self)._get_ec_formatted_sequence(number)
