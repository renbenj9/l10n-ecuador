# -*- coding: utf-8 -*-
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    contribuyenteespecial = fields.Integer(
        'Contr. Especial No.', )

    obl_conta = fields.Selection([
        ('1', 'SI'),
        ('2', 'NO'),
    ], string='Llevar Contabilidad', )

    reg_micro = fields.Selection([
        ('1', 'SI'),
        ('2', 'NO'),
    ], string='Régimen PYMES', )

    age_reten = fields.Char('Agente de retención',help="Coloque cero (0) si no es agente")
    
    reg_rimpe = fields.Selection([
        ('1', 'Régimen General'),
        ('2', 'CONTRIBUYENTE RÉGIMEN RIMPE'),
        ('3', 'Contribuyente Negocio Popular - Régimen RIMPE'),
    ], string='Régimen RIMPE', )
