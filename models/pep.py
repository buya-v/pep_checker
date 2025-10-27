from odoo import models, fields, api

class PEPPerson(models.Model):
    _name = 'pep.person'
    _description = 'Politically Exposed Person'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Full Name', required=True, tracking=True)
    date_of_birth = fields.Date(string='Date of Birth')
    nationality = fields.Many2one('res.country', string='Nationality', tracking=True)
    position = fields.Char(string='Position/Role', tracking=True)
    organization = fields.Char(string='Organization/Institution', tracking=True)
    pep_type = fields.Selection([
        ('domestic', 'Domestic PEP'),
        ('foreign', 'Foreign PEP'),
        ('international', 'International Organization PEP'),
        ('related', 'Related/Close Associate'),
    ], string='PEP Type', required=True, tracking=True)
    status = fields.Selection([
        ('active', 'Active'),
        ('former', 'Former PEP'),
        ('deceased', 'Deceased'),
    ], string='Status', default='active', tracking=True)
    start_date = fields.Date(string='Position Start Date', tracking=True)
    end_date = fields.Date(string='Position End Date', tracking=True)
    risk_level = fields.Selection([
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
    ], string='Risk Level', compute='_compute_risk_level', store=True, tracking=True)
    source = fields.Text(string='Information Source', tracking=True)
    notes = fields.Text(string='Additional Notes', tracking=True)
    active = fields.Boolean(default=True)
    last_checked = fields.Datetime(string='Last Checked', default=fields.Datetime.now)
    
    @api.depends('pep_type', 'position', 'status')
    def _compute_risk_level(self):
        for record in self:
            if record.status == 'deceased':
                record.risk_level = 'low'
            elif record.pep_type in ['foreign', 'international']:
                record.risk_level = 'high'
            elif record.pep_type == 'domestic':
                record.risk_level = 'medium'
            else:  # related/close associate
                record.risk_level = 'low'

class PEPScreening(models.Model):
    _name = 'pep.screening'
    _description = 'PEP Screening Record'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'screening_date desc'

    name = fields.Char(string='Name to Screen', required=True)
    date_of_birth = fields.Date(string='Date of Birth')
    nationality = fields.Many2one('res.country', string='Nationality')
    screening_date = fields.Datetime(string='Screening Date', default=fields.Datetime.now, required=True)
    result = fields.Selection([
        ('match', 'PEP Match Found'),
        ('possible', 'Possible Match'),
        ('no_match', 'No Match'),
    ], string='Screening Result', tracking=True)
    matched_pep_id = fields.Many2one('pep.person', string='Matched PEP')
    confidence_score = fields.Float(string='Confidence Score', help="Match confidence percentage")
    screened_by = fields.Many2one('res.users', string='Screened By', default=lambda self: self.env.user)
    notes = fields.Text(string='Screening Notes')
    
    def action_screen_name(self):
        self.ensure_one()
        # TODO: Implement name screening logic
        self.screening_date = fields.Datetime.now()
        return True