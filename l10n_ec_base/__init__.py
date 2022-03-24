# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models

from odoo import api, SUPERUSER_ID


def _set_fiscal_country(env):
    """ Sets the fiscal country on existing companies when installing the module.
    That field is an editable computed field. It doesn't automatically get computed
    on existing records by the ORM when installing the module, so doing that by hand
    ensures existing records will get a value for it if needed.
    """
    env['res.company'].search([]).compute_account_tax_fiscal_country()


def _auto_install_l10n(env):
    country_code = env.company.country_id.code
    if country_code:
        module_list = []
        if country_code == "EC":
            module_list.append("l10n_ec_base")
            module_ids = env["ir.module.module"].search([("name", "in", module_list), ("state", "=", "uninstalled")])
            module_ids.sudo().button_install()


def _account_post_init(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    _auto_install_l10n(env)
    _set_fiscal_country(env)
