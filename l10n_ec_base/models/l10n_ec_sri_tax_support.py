#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging

from odoo import _, fields, models


_logger = logging.getLogger(__name__)


class SriTaxSupport(models.Model):
    """SRI Tax Support"""

    _name = "l10n_ec.sri.tax.support"
    _description = __doc__

    code = fields.Char(string="Code")
    name = fields.Char(string="Name")
    description = fields.Char(string="Description")

    def name_get(self):
        result = []
        for row in self:
            name = row.name
            if row.code:
                name = f"({row.code}) {name}"
            result.append((row.id, name))
        return result
