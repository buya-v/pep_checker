from odoo import models, fields, api, _

class PEPPositionTemplate(models.Model):
    _name = 'pep.position.template'
    _description = 'PEP Position Template'
    _order = 'country_id, name'

    name = fields.Char(string='Position Title', required=True, index=True)
    category = fields.Selection(
        string='Category',
        selection=lambda self: self.env['pep.person']._fields['position'].selection,
        required=True,
        index=True
    )
    country_id = fields.Many2one('res.country', string='Country', index=True)
    year = fields.Char(string='Year / Period', index=True, help="The year or period for which this position is relevant.")
    notes = fields.Text(string='Notes')
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('name_country_year_uniq', 'unique(name, country_id, year)', 'A position with this title already exists for this country and year.')
    ]
