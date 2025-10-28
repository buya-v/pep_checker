from odoo import models, fields, api
from datetime import datetime, date
import calendar

class PEPPerson(models.Model):
    _name = 'pep.person'
    _description = 'Politically Exposed Person'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _sql_constraints = [
        ('name_dob_uniq', 'UNIQUE(name, date_of_birth)', 'A PEP person with this name and date of birth already exists.'),
    ]

    name = fields.Char(string='Full Name', required=True, tracking=True)
    date_of_birth = fields.Date(string='Date of Birth')
    nationality = fields.Many2one('res.country', string='Nationality', tracking=True, index=True)
    position = fields.Selection([
        # Foreign and Domestic PEP positions
        ('head_state', 'Head of State/Government'),
        ('minister', 'Minister/Vice Minister'),
        ('parliament', 'Member of Parliament'),
        ('senior_politician', 'Senior Politician'),
        ('senior_govt', 'Senior Government Official'),
        ('judicial', 'Senior Judicial Official'),
        ('military', 'Senior Military Official'),
        ('state_exec', 'Senior State-Owned Enterprise Executive'),
        ('party_official', 'Important Political Party Official'),
        # International Organization positions
        ('intl_director', 'Director/Deputy Director'),
        ('intl_board', 'Board Member'),
        ('intl_senior', 'Senior Management'),
        ('other', 'Other Senior Position')
    ], string='Position/Role', tracking=True, index=True, required=True)
    custom_position = fields.Char(string='Specific Position Title', tracking=True)
    organization = fields.Char(string='Organization/Institution', tracking=True, index=True)
    organization_type = fields.Selection([
        ('government', 'Government'),
        ('political_party', 'Political Party'),
        ('judiciary', 'Judiciary'),
        ('military', 'Military'),
        ('state_owned', 'State-Owned Enterprise'),
        ('international_org', 'International Organization'),
        ('other', 'Other')
    ], string='Organization Type', tracking=True)
    pep_type = fields.Selection([
        ('domestic', 'Domestic PEP'),
        ('foreign', 'Foreign PEP'),
        ('international', 'International Organization PEP')
    ], string='PEP Type', required=True, tracking=True)
    status = fields.Selection([
        ('active', 'Active'),
        ('former', 'Former PEP'),
        ('deceased', 'Deceased'),
    ], string='Status', default='active', tracking=True)
    start_date = fields.Date(string='Position Start Date', tracking=True, index=True)
    end_date = fields.Date(string='Position End Date', tracking=True, index=True)
    risk_level = fields.Selection([
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
    ], string='Risk Level', compute='_compute_risk_level', store=True, tracking=True)
    
    # EDD (Enhanced Due Diligence) Fields
    edd_status = fields.Selection([
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('review_needed', 'Review Needed')
    ], string='EDD Status', default='pending', tracking=True)
    edd_last_review = fields.Date(string='Last EDD Review', tracking=True)
    edd_next_review = fields.Date(string='Next EDD Review', compute='_compute_next_review', store=True)
    
    # Source of Wealth and Funds
    source_of_wealth = fields.Text(string='Source of Wealth', tracking=True, 
                                 help="Description of how the individual's overall wealth was acquired")
    source_of_funds = fields.Text(string='Source of Funds', tracking=True,
                                help="Origin of the funds involved in the business relationship")
    
    # Approval and Monitoring
    senior_approval_id = fields.Many2one('res.users', string='Senior Management Approval By', tracking=True)
    senior_approval_date = fields.Datetime(string='Approval Date', tracking=True)
    monitoring_frequency = fields.Selection([
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('semi_annual', 'Semi-Annual'),
        ('annual', 'Annual')
    ], string='Monitoring Frequency', default='quarterly', tracking=True)
    
    # Related persons will be accessible through the inverse field in pep.relationship
    family_members_ids = fields.One2many('pep.relationship', 'pep_id', 
                                       domain=[('relationship_type', '=', 'family')],
                                       string='Family Members')
    close_associates_ids = fields.One2many('pep.relationship', 'pep_id',
                                         domain=[('relationship_type', '=', 'associate')],
                                         string='Close Associates')
    
    source = fields.Text(string='Information Source', tracking=True)
    notes = fields.Text(string='Additional Notes', tracking=True)
    active = fields.Boolean(default=True)
    last_checked = fields.Datetime(string='Last Checked', default=fields.Datetime.now, index=True)
    
    @api.depends('pep_type', 'position', 'status', 'end_date')
    def _compute_risk_level(self):
        for record in self:
            if record.status == 'deceased':
                record.risk_level = 'low'
            elif record.status == 'former':
                # Check if it's been more than 18 months since end of position
                if record.end_date and (datetime.now().date() - record.end_date).days > 548:  # 18 months * 30.44 days
                    record.risk_level = 'low'
                else:
                    record.risk_level = 'medium'
            elif record.pep_type == 'foreign':
                record.risk_level = 'high'
            elif record.pep_type == 'international':
                if record.position in ['intl_director', 'intl_board']:
                    record.risk_level = 'high'
                else:
                    record.risk_level = 'medium'
            else:  # domestic PEP
                if record.position in ['head_state', 'minister', 'senior_politician']:
                    record.risk_level = 'high'
                else:
                    record.risk_level = 'medium'

    @api.depends('edd_last_review', 'monitoring_frequency')
    def _compute_next_review(self):
        for record in self:
            if not record.edd_last_review:
                record.edd_next_review = fields.Date.today()
                continue

            if record.monitoring_frequency == 'monthly':
                months = 1
            elif record.monitoring_frequency == 'quarterly':
                months = 3
            elif record.monitoring_frequency == 'semi_annual':
                months = 6
            else:  # annual
                months = 12

            # Add months to a date without external dependencies (safe for environments
            # where dateutil is not available). We calculate the target year/month and
            # clamp the day to the last day of that month if necessary.
            def _add_months(d, m):
                month = d.month - 1 + m
                year = d.year + month // 12
                month = month % 12 + 1
                day = min(d.day, calendar.monthrange(year, month)[1])
                return date(year, month, day)

            # edd_last_review is a date field; ensure it's a date instance
            last = record.edd_last_review
            if isinstance(last, datetime):
                last = last.date()
            record.edd_next_review = _add_months(last, months)

    def action_request_approval(self):
        """Request senior management approval for PEP relationship"""
        self.ensure_one()
        if not self.senior_approval_id:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Request Senior Management Approval',
                'res_model': 'pep.approval.wizard',
                'view_mode': 'form',
                'target': 'new',
                'context': {'default_pep_id': self.id}
            }
        return True

    def action_schedule_edd_review(self):
        """Schedule the next Enhanced Due Diligence review"""
        self.ensure_one()
        self.edd_last_review = fields.Date.today()
        # This will trigger the computation of next_review
        return True

class PEPRelationship(models.Model):
    _name = 'pep.relationship'
    _description = 'PEP Relationship'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Name', required=True, tracking=True)
    pep_id = fields.Many2one('pep.person', string='Related PEP', required=True, 
                            ondelete='cascade', index=True)
    relationship_type = fields.Selection([
        ('family', 'Family Member'),
        ('associate', 'Close Associate')
    ], string='Relationship Type', required=True, tracking=True, default=lambda self: self._context.get('default_relationship_type', 'family'))
    
    # Family relationship specifics
    family_relation = fields.Selection([
        ('spouse', 'Spouse/Partner'),
        ('child', 'Child'),
        ('child_spouse', "Child's Spouse/Partner"),
        ('parent', 'Parent'),
        ('sibling', 'Sibling'),
        ('other', 'Other Family Member')
    ], string='Family Relation')
    
    # Close associate specifics
    association_type = fields.Selection([
        ('business_partner', 'Business Partner'),
        ('joint_owner', 'Joint Beneficial Owner'),
        ('legal_arrangement', 'Legal Arrangement Beneficial Owner'),
        ('close_business', 'Close Business Relationship'),
        ('other', 'Other Association')
    ], string='Association Type')
    
    date_of_birth = fields.Date(string='Date of Birth')
    nationality = fields.Many2one('res.country', string='Nationality')
    
    # Enhanced Due Diligence for relationships
    edd_required = fields.Boolean(string='EDD Required', 
                                help="Whether Enhanced Due Diligence is required for this relationship",
                                default=True)
    source_of_wealth = fields.Text(string='Source of Wealth', tracking=True)
    source_of_funds = fields.Text(string='Source of Funds', tracking=True)
    
    relationship_notes = fields.Text(string='Relationship Details', tracking=True)
    verification_date = fields.Date(string='Verification Date', tracking=True)
    verification_source = fields.Text(string='Verification Source', tracking=True)
    active = fields.Boolean(default=True)
    
    @api.onchange('relationship_type')
    def _onchange_relationship_type(self):
        self.family_relation = False
        self.association_type = False

    @api.constrains('relationship_type', 'family_relation', 'association_type')
    def _check_relation_consistency(self):
        for record in self:
            if record.relationship_type == 'family' and not record.family_relation:
                raise models.ValidationError('Family relation must be specified for family members')
            if record.relationship_type == 'associate' and not record.association_type:
                raise models.ValidationError('Association type must be specified for close associates')

class PEPScreening(models.Model):
    _name = 'pep.screening'
    _description = 'PEP Screening Record'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'screening_date desc'

    name = fields.Char(string='Name to Screen', required=True)
    date_of_birth = fields.Date(string='Date of Birth')
    nationality = fields.Many2one('res.country', string='Nationality', index=True)
    screening_date = fields.Datetime(string='Screening Date', default=fields.Datetime.now, required=True, index=True)
    result = fields.Selection([
        ('match', 'PEP Match Found'),
        ('possible', 'Possible Match'),
        ('no_match', 'No Match'),
    ], string='Screening Result', tracking=True)
    matched_pep_id = fields.Many2one('pep.person', string='Matched PEP', index=True)
    confidence_score = fields.Float(string='Confidence Score', help="Match confidence percentage")
    screened_by = fields.Many2one('res.users', string='Screened By', default=lambda self: self.env.user, index=True)
    notes = fields.Text(string='Screening Notes')
    
    def action_screen_name(self):
        self.ensure_one()
        # TODO: Implement name screening logic
        self.screening_date = fields.Datetime.now()
        return True


class PEPApprovalWizard(models.TransientModel):
    _name = 'pep.approval.wizard'
    _description = 'PEP Senior Approval Wizard'

    pep_id = fields.Many2one('pep.person', string='PEP', required=True)
    approved_by = fields.Many2one('res.users', string='Approved By', default=lambda self: self.env.user)
    note = fields.Text(string='Approval Note')

    def action_confirm_approval(self):
        self.ensure_one()
        if not self.pep_id:
            return {'type': 'ir.actions.act_window_close'}
        self.pep_id.senior_approval_id = self.approved_by.id
        self.pep_id.senior_approval_date = fields.Datetime.now()
        # Mark EDD status as completed when approval is granted
        self.pep_id.edd_status = 'completed'
        return {'type': 'ir.actions.act_window_close'}