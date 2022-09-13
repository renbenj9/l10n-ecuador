# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from datetime import datetime, date
from odoo.exceptions import UserError, ValidationError

class AccountMove(models.Model):
    _inherit = "account.move"

    is_draft = fields.Boolean(string='Is Draft', default=False)

    def button_draft(self):
        res = super(AccountMove, self).button_draft()
        self.is_draft = True
        return res

    @api.depends('posted_before', 'state', 'journal_id', 'date')
    def _compute_name(self):
        for rec in self:
            if rec.journal_id.type in ('sale', 'purchase') and rec.move_type in (
            'in_invoice', 'in_refund', 'out_invoice', 'out_refund') and self.name in (False, '/'):
                rec.name = '/'
            else:
                super(AccountMove, self)._compute_name()

    def write(self, vals):
        if self.is_draft == False:
            if 'state' in vals:
                if vals['state'] in ('posted'):
                    if self.journal_id.type in ('sale', 'purchase'):
                        if self.move_type in ('out_invoice', 'in_invoice', 'out_receipt', 'in_receipt'):
                            if not self.journal_id.bi_sequence_id:
                                raise ValidationError('Add Sequence In Journal')
                            else:
                                seq = self.journal_id.l10n_ec_entity + "-" + self.journal_id.l10n_ec_emission + "-" + self.journal_id.bi_sequence_id._next()
                                vals['name'] = seq
                                self.journal_id.sudo().write({'bi_sequence_next_number': self.env['ir.sequence'].search(
                                    [('id', '=', self.journal_id.bi_sequence_id.id)]).number_next_actual})
                        elif self.move_type in ('out_refund', 'in_refund'):
                            if not self.journal_id.bi_refund_sequence_id:
                                raise ValidationError('Add Refund/Credit Note Sequence In Journal')
                            else:
                                seq = self.journal_id.l10n_ec_entity + "-" + self.journal_id.l10n_ec_emission + "-" + self.journal_id.bi_refund_sequence_id._next()
                                vals['name'] = seq
                                self.journal_id.sudo().write({'bi_refund_sequence_next_number': self.env[
                                    'ir.sequence'].search(
                                    [('id', '=', self.journal_id.bi_refund_sequence_id.id)]).number_next_actual})
                elif vals['state'] in ('draft', 'cancel'):
                    if self.journal_id.type in ('sale', 'purchase'):
                        for rec in self:
                            self.name = rec.name

        return super(AccountMove, self).write(vals)
