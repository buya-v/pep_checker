from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, date
import re
import json
import logging

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    requests = None
    BeautifulSoup = None

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

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'X-Requested-With': 'XMLHttpRequest',
}


class PEPPerson(models.Model):
    _name = 'pep.person'
    _description = 'Politically Exposed Person'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _sql_constraints = [
        ('name_dob_uniq', 'UNIQUE(name, date_of_birth)', _('A PEP person with this name and date of birth already exists.')),
    ]

    name = fields.Char(string='Full Name', required=True, tracking=True)
    name_phonetic = fields.Char(string='Phonetic Name', compute='_compute_phonetic_name', store=True, index=True,
                                help="Phonetic representation of the name for advanced searching.")
    date_of_birth = fields.Date(string='Date of Birth')
    nationality = fields.Many2one('res.country', string='Nationality', tracking=True, index=True)
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
    start_date = fields.Integer(string='Position Start Year', tracking=True, index=True)
    end_date = fields.Integer(string='Position End Year', tracking=True, index=True)
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
                raise ValidationError(_('International PEPs must be associated with international organizations.'))

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
                    raise ValidationError(
                        _("Invalid name format for a Mongolian PEP. The required format is 'Эцэг/эхийн нэр Өөрийн нэр (Firstname Surname)', for example: 'Ухнаа Хүрэлсүх (Khurelsukh Ukhnaa)'."))

    @api.depends('pep_type', 'position', 'status', 'end_date')
    def _compute_risk_level(self):
        for record in self:
            if record.status == 'deceased':
                record.risk_level = 'low'
            elif record.status == 'former':
                # If a PEP has been out of office for more than 5 years, risk can be lowered.
                # This requires end_date to be set.
                if record.end_date and (date.today().year - record.end_date) > 5:
                    record.risk_level = 'low'
                else:
                    record.risk_level = 'medium'
            elif record.pep_type == 'domestic':
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

    def _get_xacxom_search_url(self):
        return self.env['ir.config_parameter'].sudo().get_param(
            'pep_checker.xacxom_search_url', "https://xacxom.iaac.mn/xacxom/search")

    def action_edd_with_xacxom(self):
        """
        Performs EDD by scraping the official Mongolian source (xacxom.iaac.mn),
        updating the PEP record with the findings, and refreshing monitoring dates.
        """
        self.ensure_one()
        if not requests or not BeautifulSoup:
            raise UserError(_("The 'requests' and 'beautifulsoup4' libraries are required. Please install them using: pip install requests beautifulsoup4"))

        # Parse the Cyrillic name into patronymic (last_name) and given name (firstname)
        cyrillic_name_part = self.name.split('(')[0].strip()
        name_parts = cyrillic_name_part.split()
        if len(name_parts) < 2:
            raise UserError(_("The PEP's name '%s' does not seem to be in the 'Patronymic GivenName' format and cannot be searched automatically.", self.name))

        search_url = self._get_xacxom_search_url()
        # Construct the payload with specific form fields
        payload = {
            'last_name': name_parts[0],
            'first_name': " ".join(name_parts[1:]),
        }

        _logger.info("Verifying PEP '%s' against official source with search params: %s", self.name, payload)

        try:
            # The form uses a GET request, so we use 'params'
            response = requests.get(search_url, params=payload, headers=HEADERS, timeout=30)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            raise UserError(_("Failed to connect to the official source website. Error: %s", e))

        soup = BeautifulSoup(response.content, 'html.parser')
        table = soup.find('table', class_='table')
        scraped_data = []

        if table:
            rows = table.find_all('tr')
            for row in rows[1:]:  # Skip header
                cols = row.find_all('td')
                if len(cols) >= 5:
                    # Corrected column mapping based on HTML sample
                    declaration_year = cols[2].text.strip() if len(cols) > 2 else ''
                    last_name = cols[3].text.strip() if len(cols) > 3 else ''
                    first_name = cols[4].text.strip() if len(cols) > 4 else ''
                    full_name = f"{last_name} {first_name}"
                    organization = cols[5].text.strip() if len(cols) > 5 else ''
                    position = cols[6].text.strip() if len(cols) > 6 else ''
                    aid_input = cols[1].find('input', class_='aid_number') if len(cols) > 1 else None
                    aid_number = aid_input['value'] if aid_input else ''
                    scraped_data.append({
                        'name': full_name,
                        'position': position,
                        'organization': organization,
                        'declaration_year': declaration_year,
                        'aid_number': aid_number,
                    })

        if scraped_data:
            update_vals = {
                'last_checked': fields.Datetime.now(),
                'edd_last_review': fields.Date.today(),
                'source': 'https://xacxom.iaac.mn',
            }

            # Calculate min/max years for the position timeline
            declaration_years = [int(entry['declaration_year']) for entry in scraped_data if entry.get('declaration_year', '').isdigit()]
            if declaration_years:
                update_vals['start_date'] = min(declaration_years)
                update_vals['end_date'] = max(declaration_years)

            # Format the scraped data into a readable summary for the notes field
            summary_lines = [
                "\n--- Official Source Verification (xacxom.iaac.mn) ---",
                f"Verification Date: {fields.Date.today()}",
                f"Found {len(scraped_data)} declaration(s) for '{self.name}':"
            ]
            for entry in sorted(scraped_data, key=lambda x: x.get('declaration_year', '0'), reverse=True):
                summary_lines.append(
                    f"- Year: {entry.get('declaration_year', 'N/A')}, Position: {entry.get('position', 'N/A')}, Organization: {entry.get('organization', 'N/A')}"
                )
            
            update_vals['notes'] = (self.notes + "\n" if self.notes else "") + "\n".join(summary_lines)
            
            self.write(update_vals)
            _logger.info("Appended verification summary to notes for PEP %s", self.name)

        return True

    @api.model
    def _run_edd_review_scheduler(self):
        """
        Scheduled action to find high-risk PEPs needing an EDD review.
        This method is intended to be called by an ir.cron job.
        """
        _logger.info("Running EDD review scheduler...")
        peps_for_review = self.search([
            ('risk_level', '=', 'high'),
            ('edd_next_review', '<=', fields.Date.today()),
            ('status', '=', 'active'),
            ('edd_status', '!=', 'review_needed'), # Avoid creating duplicate activities
        ])

        if not peps_for_review:
            _logger.info("No high-risk PEPs found for scheduled EDD review.")
            return

        _logger.info(f"Found {len(peps_for_review)} high-risk PEPs for EDD review.")

        manager_group = self.env.ref('pep_checker.group_pep_manager', raise_if_not_found=False)
        activity_type = self.env.ref('mail.mail_activity_data_todo', raise_if_not_found=False)

        if not manager_group or not activity_type:
            _logger.warning("PEP Manager group or 'To Do' activity type not found. Cannot assign review activities.")
            return

        for pep in peps_for_review:
            pep.edd_status = 'review_needed'
            # Create a single activity for the manager group (no specific user assigned)
            self.env['mail.activity'].create({
                'res_model_id': self.env['ir.model']._get(pep._name).id,
                'res_id': pep.id,
                'activity_type_id': activity_type.id,
                'summary': _('Enhanced Due Diligence Review Required'),
                'note': _('Please perform the scheduled EDD review for the high-risk PEP: %s.', pep.name),
                'user_id': False, # Unassigned, will be visible to the group
                'date_deadline': fields.Date.today(),
            })
        _logger.info("Successfully created EDD review activities for %d PEPs.", len(peps_for_review))

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
                raise ValidationError(_('Family relation must be specified for family members.'))
            if record.relationship_type == 'associate' and not record.association_type:
                raise ValidationError(_('Association type must be specified for close associates.'))

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
            raise UserError(_("The 'google-generativeai' library is not installed. Please install it using: pip install google-generativeai"))

        # Get API Key from Odoo's system parameters for security
        api_key = self.env['ir.config_parameter'].sudo().get_param('pep_checker.google_api_key')
        if not api_key:
            raise UserError(_("Google AI API key is not configured. Please set 'pep_checker.google_api_key' in System Parameters."))

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
            raise UserError(_("The AI returned a response that could not be processed as JSON. Please check the logs for the raw response. Raw response:\n\n%s", response.text))
        except Exception as e:
            _logger.error("An error occurred during AI screening: %s", str(e))
            raise UserError(_("An error occurred while contacting the AI service: %s", e))

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