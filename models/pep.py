from odoo import models, fields, api
from datetime import datetime, date
import re
import json
import logging

try:
    from dateutil.relativedelta import relativedelta
except ImportError:
    relativedelta = None

try:
    import google.generativeai as genai
except ImportError:
    genai = None

try:
    import jellyfish
except ImportError:
    jellyfish = None

_logger = logging.getLogger(__name__)


class PEPPerson(models.Model):
    _name = 'pep.person'
    _description = 'Politically Exposed Person'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _sql_constraints = [
        ('name_dob_uniq', 'UNIQUE(name, date_of_birth)', 'A PEP person with this name and date of birth already exists.'),
    ]

    name = fields.Char(string='Full Name', required=True, tracking=True)
    name_phonetic = fields.Char(string='Phonetic Name', compute='_compute_phonetic_name', store=True, index=True,
                                help="Phonetic representation of the name for advanced searching.")
    date_of_birth = fields.Date(string='Date of Birth')
    nationality = fields.Many2one('res.country', string='Nationality', tracking=True, index=True)
    is_mongolian_pep = fields.Boolean(string="Mongolian PEP", compute='_compute_is_mongolian_pep', store=True,
                                     help="Indicates if the person is a PEP according to Mongolian law.")
    position = fields.Selection([
        # Positions based on Mongolian Law & FATF Recommendations
        ('head_state', 'Head of State/Government'),
        ('parliament', 'Member of Parliament'),
        ('governor', 'Governor of Province/ Capital City'),
        ('judicial', 'Senior Judicial Official'),
        ('central_bank_board', 'Member of Court of Auditors or Board of a Central Bank'),
        ('diplomat_military', 'Ambassador or High-ranking Military Officer'),
        ('state_enterprise', 'Senior State-Owned Enterprise Executive'),
        ('party_official', 'Senior Political Party Official'),
        # International Organization positions
        ('intl_director', 'Director/Deputy Director (International Org)'),
        ('intl_board', 'Board Member (International Org)'),
        ('intl_senior', 'Senior Management (International Org)'),
        ('other', 'Other (Not defined in Mongolian Law)')
    ], string='Position/Role', tracking=True, index=True, required=True)
    custom_position = fields.Char(string='Specific Position Title', tracking=True)
    organization = fields.Char(string='Organization/Institution', tracking=True, index=True, required=True)
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
    ], string='PEP Type', compute='_compute_pep_type', store=True, tracking=True)
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
    source_url = fields.Char(string='Source URL', help='URL to the source document or page', index=True)
    source_date = fields.Date(string='Source Date', help='Date when the source was published or captured', index=True)
    notes = fields.Text(string='Additional Notes', tracking=True)
    # Self-declaration tracking
    self_declared = fields.Boolean(string='Self-Declared', tracking=True,
                               help="Whether the person self-declared their PEP status")
    self_declaration_date = fields.Date(string='Self-Declaration Date', tracking=True)

    # Record retention tracking
    retention_period = fields.Integer(string='Record Retention Period (Years)', default=5,
                                  help="Minimum period in years to retain PEP records after relationship end")
    retention_end_date = fields.Date(string='Retention End Date', 
                                   compute='_compute_retention_end_date', store=True)

    active = fields.Boolean(default=True)
    last_checked = fields.Datetime(string='Last Checked', default=fields.Datetime.now, index=True)
    
    @api.depends('name')
    def _compute_phonetic_name(self):
        if not jellyfish:
            _logger.warning("The 'jellyfish' library is not installed. Phonetic search will be disabled.")
            for record in self:
                record.name_phonetic = False
            return
        for record in self:
            record.name_phonetic = jellyfish.metaphone(record.name) if record.name else False
    @api.constrains('pep_type', 'position', 'organization_type')
    def _check_pep_type_consistency(self):
        for record in self:
            if record.pep_type == 'international' and record.organization_type != 'international_org':
                raise models.ValidationError('International PEPs must be associated with international organizations')

    @api.depends('nationality', 'organization_type')
    def _compute_pep_type(self):
        company_country = self.env.company.country_id
        for record in self:
            if record.organization_type == 'international_org':
                record.pep_type = 'international'
            elif record.nationality and company_country and record.nationality == company_country:
                record.pep_type = 'domestic'
            else:
                # If nationality or company country is not set, or they differ, default to foreign
                record.pep_type = 'foreign'
    
    @api.constrains('name', 'nationality')
    def _check_mongolian_name_format(self):
        """
        For Mongolian PEPs, enforce the name format:
        'Cyrillic Name (Latin Name)'
        """
        # Regex to check for:
        # - Cyrillic characters, spaces, and dots (for initials).
        # - A space, then a Latin name in parentheses.
        # This is more flexible to handle AI responses with initials.
        mongolian_name_pattern = re.compile(r'^[\u0400-\u04FF\s\.\-]+\s\([\w\s\.\-]+\)$')
        for record in self:
            if record.nationality.code == 'MN':
                if not record.name or not mongolian_name_pattern.match(record.name):
                    raise models.ValidationError(
                        "Invalid name format for a Mongolian PEP. The required format is 'Эцэг/эхийн нэр Өөрийн нэр (Firstname Surname)', for example: 'Ухнаа Хүрэлсүх (Khurelsukh Ukhnaa)'.")

    @api.depends('end_date', 'retention_period')
    def _compute_retention_end_date(self):
        for record in self:
            if record.end_date and record.retention_period > 0 and relativedelta:
                record.retention_end_date = record.end_date + relativedelta(years=record.retention_period)
            elif record.end_date and record.retention_period > 0:
                # Fallback if dateutil is not available
                record.retention_end_date = date(record.end_date.year + record.retention_period, record.end_date.month, record.end_date.day)
            else:
                record.retention_end_date = False

    @api.depends('nationality', 'position')
    def _compute_is_mongolian_pep(self):
        # Define the specific positions that are considered PEPs under Mongolian Law
        mongolian_pep_positions = [
            'head_state',
            'parliament',
            'governor',
        ]
        for record in self:
            is_mn_position = record.position in mongolian_pep_positions
            record.is_mongolian_pep = is_mn_position

    @api.depends('pep_type', 'position', 'status', 'end_date')
    def _compute_risk_level(self):
        for record in self:
            if record.status == 'deceased':
                record.risk_level = 'low'
            elif record.status == 'former':
                # A former PEP may be considered lower risk after a certain period (e.g., 18 months)
                # has passed since they left their position.
                if record.end_date and relativedelta and (fields.Date.today() > record.end_date + relativedelta(months=18)):
                    record.risk_level = 'low'
                else:
                    record.risk_level = 'medium'
            elif record.is_mongolian_pep:
                record.risk_level = 'high'
            elif record.pep_type == 'foreign':
                record.risk_level = 'high'
            elif record.pep_type == 'international':
                if record.position in ('intl_director', 'intl_board'):
                    record.risk_level = 'high'
                else:
                    record.risk_level = 'medium'

    @api.depends('edd_last_review', 'monitoring_frequency')
    def _compute_next_review(self):
        for record in self:
            if not record.edd_last_review:
                record.edd_next_review = fields.Date.today()
                continue

            if not relativedelta:
                record.edd_next_review = False  # Or handle with fallback
                continue

            months_to_add = 0
            if record.monitoring_frequency == 'monthly':
                months_to_add = 1
            elif record.monitoring_frequency == 'quarterly':
                months_to_add = 3
            elif record.monitoring_frequency == 'semi_annual':
                months_to_add = 6
            elif record.monitoring_frequency == 'annual':
                months_to_add = 12

            if months_to_add > 0:
                record.edd_next_review = record.edd_last_review + relativedelta(months=months_to_add)
            else:
                record.edd_next_review = False

    def action_request_approval(self):
        """Request senior management approval for PEP relationship"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Request Senior Management Approval',
            'res_model': 'pep.approval.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_pep_id': self.id}
        }

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
    
    # Enhanced screening information
    screening_type = fields.Selection([
        ('initial', 'Initial Screening'),
        ('periodic', 'Periodic Review'),
        ('trigger', 'Trigger Event'),
        ('exit', 'Exit Screening')
    ], string='Screening Type', required=True, default='initial', tracking=True)
    
    trigger_reason = fields.Selection([
        ('news', 'Adverse News'),
        ('transaction', 'Unusual Transaction'),
        ('structure', 'Change in Structure'),
        ('other', 'Other Trigger')
    ], string='Trigger Reason', tracking=True)
    
    result = fields.Selection([
        ('match', 'PEP Match Found'),
        ('possible', 'Possible Match'),
        ('no_match', 'No Match'),
    ], string='Screening Result', tracking=True)
    
    matched_pep_id = fields.Many2one('pep.person', string='Matched PEP', index=True)
    confidence_score = fields.Float(string='Confidence Score', help="Match confidence percentage")
    screened_by = fields.Many2one('res.users', string='Screened By', default=lambda self: self.env.user, index=True)
    
    # Documentation and evidence
    screening_method = fields.Selection([
        ('database', 'PEP Database'),
        ('media', 'Media Search'),
        ('official', 'Official Lists'),
        ('manual', 'Manual Research'),
        ('ai_screening', 'AI Screening')
    ], string='Screening Method', required=True, tracking=True)
    
    database_used = fields.Selection([
        ('worldcheck', 'World-Check'),
        ('dowjones', 'Dow Jones'),
        ('refinitiv', 'Refinitiv'),
        ('other', 'Other Database')
    ], string='Database Used')
    
    evidence_refs = fields.Text(string='Evidence References', 
                              help="References to documents, articles, or database entries that support the screening result")
    notes = fields.Text(string='Screening Notes')
    
    @api.onchange('screening_type')
    def _onchange_screening_type(self):
        if self.screening_type != 'trigger':
            self.trigger_reason = False
            
    @api.onchange('screening_method')
    def _onchange_screening_method(self):
        if self.screening_method != 'database':
            self.database_used = False
    
    def action_screen_name(self):
        self.ensure_one()

        # --- Step 1: Search internal PEP database first ---
        _logger.info("Performing internal PEP database check for: %s", self.name)
        
        # Build a search domain that uses both phonetic matching and a direct 'ilike' match.
        search_domain = [('name', 'ilike', self.name)]
        if jellyfish and self.name:
            phonetic_code = jellyfish.metaphone(self.name)
            # The '|' creates an OR condition in the search domain.
            search_domain = ['|', ('name_phonetic', '=', phonetic_code)] + search_domain

        _logger.info("Using search domain: %s", search_domain)

        matched_peps = self.env['pep.person'].search(search_domain)

        if matched_peps:
            _logger.info("Found %d potential match(es) in the internal database.", len(matched_peps))
            # If matches are found, update the screening record and stop.
            if len(matched_peps) == 1:
                # If only one match, we can consider it a strong candidate.
                pep = matched_peps[0]
                self.write({
                    'result': 'match',
                    'matched_pep_id': pep.id,
                    'notes': f"Internal DB Match: Found '{pep.name}' ({pep.pep_type}, {pep.nationality.name}).",
                    'screening_method': 'database',
                })
            else:
                # If multiple matches, list them for manual review.
                pep_names = ", ".join(matched_peps.mapped('name'))
                self.write({
                    'result': 'possible',
                    'notes': f"Internal DB: Found multiple possible matches: {pep_names}",
                    'screening_method': 'database',
                })
            self.screening_date = fields.Datetime.now()
            return True # End the process here

        # --- Step 2: If no internal match, proceed with AI screening ---
        _logger.info("No internal match found. Proceeding with AI screening for: %s", self.name)
        if not genai:
            raise models.UserError("The 'google-generativeai' library is not installed. Please install it using: pip install google-generativeai")

        # Get API Key from Odoo's system parameters for security
        api_key = self.env['ir.config_parameter'].sudo().get_param('pep_checker.google_api_key')
        if not api_key:
            raise models.UserError("Google AI API key is not configured. Please set 'pep_checker.google_api_key' in System Parameters.")

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.5-flash')

        # Construct a detailed prompt for the AI
        prompt_parts = [
            f"Please act as a compliance expert. Analyze public information for the following individual to determine if they are a Politically Exposed Person (PEP):",
            f"Name: {self.name}",
        ]
        if self.date_of_birth:
            prompt_parts.append(f"Date of Birth: {self.date_of_birth.strftime('%Y-%m-%d')}")
        if self.nationality:
            prompt_parts.append(f"Nationality: {self.nationality.name}")

        prompt_parts.extend([
            "\nBased on your analysis, provide a response in JSON format with the following keys:",
            '- "is_pep": (boolean) true if they are a PEP, otherwise false.',
            '- "position": (string) The specific political title or role held, if any.',
            '- "country": (string) The country associated with their political role.',
            '- "summary": (string) A brief summary of why they are or are not considered a PEP.',
            '- "source_urls": (array of strings) A list of up to 3 URLs to public sources (like Wikipedia, official government sites, or reputable news articles) that support your conclusion.',
            "\nIf you cannot find any information, return a JSON object with 'is_pep' as false and a summary explaining that no definitive information was found."
        ])
        prompt = "\n".join(prompt_parts)

        try:
            _logger.info("Sending prompt to Gemini API for PEP screening: %s", self.name)
            response = model.generate_content(prompt)
            
            # Clean the response to extract only the JSON part
            response_text = response.text.strip().replace('```json', '').replace('```', '').strip()
            result_data = json.loads(response_text)

            _logger.info("Received AI response: %s", result_data)

            # Update the screening record with the AI's findings
            if result_data.get('is_pep'):
                self.write({
                    'result': 'possible', # Set to 'possible' for manual review
                    'notes': result_data.get('summary', 'No summary provided.'),
                    'evidence_refs': "\n".join(result_data.get('source_urls', [])),
                    'screening_method': 'ai_screening',
                })
            else:
                self.write({
                    'result': 'no_match',
                    'notes': result_data.get('summary', 'No match found.'),
                    'screening_method': 'ai_screening',
                })

        except json.JSONDecodeError:
            _logger.error("Failed to decode JSON from AI response: %s", response.text)
            raise models.UserError(_("The AI returned a response that could not be processed as JSON. Please check the logs for the raw response. Raw response:\n\n%s", response.text))
        except Exception as e:
            _logger.error("An error occurred during AI screening: %s", str(e))
            raise models.UserError(f"An error occurred while contacting the AI service: {e}")

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