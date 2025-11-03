from odoo import models, fields, api, _
from odoo.exceptions import UserError
import json
import logging

try:
    import google.generativeai as genai
except ImportError:
    genai = None

try:
    import openai
except ImportError:
    openai = None

_logger = logging.getLogger(__name__)

class PEPAISearchWizard(models.TransientModel):
    _name = 'pep.ai.search.wizard'
    _description = 'PEP AI Search Wizard'

    country_id = fields.Many2one('res.country', string='Country', required=True, default=lambda self: self.env.company.country_id)
    position = fields.Char(string='Position/Role', required=True, help="Enter a specific role, e.g., 'Minister of Finance', 'Central Bank Governor'.")
    year = fields.Char(string='Year / Period', required=True, default='current', help="Enter a year (e.g., 2024), a range (e.g., 2020-2024), or a term (e.g., 'current').")
    ai_provider = fields.Selection([
        ('gemini', 'Google Gemini'),
        ('openai', 'OpenAI ChatGPT')
    ], string='AI Provider', default='gemini', required=True)
    ai_model = fields.Char(string='AI Model', default='gemini-2.5-flash', required=True)
    result_line_ids = fields.One2many('pep.ai.search.result.line', 'wizard_id', string='Search Results')

    @api.onchange('ai_provider')
    def _onchange_ai_provider(self):
        if self.ai_provider == 'gemini':
            self.ai_model = 'gemini-2.5-flash'
        elif self.ai_provider == 'openai':
            self.ai_model = 'gpt-5'
        else:
            self.ai_model = False

    def action_search_pep_with_ai(self):
        self.ensure_one()
        
        # Clear previous results
        self.result_line_ids.unlink()

        try:
            response_text = ""
            if self.ai_provider == 'gemini':
                response_text = self._search_with_gemini()
            elif self.ai_provider == 'openai':
                response_text = self._search_with_openai()

            return self._process_ai_response(response_text)
        except (openai.RateLimitError, openai.APIStatusError) as e:
            _logger.error("OpenAI API Error: %s", e)
            # Provide a more specific error message for common OpenAI issues
            raise UserError(_("An error occurred with the OpenAI service: %s\n\nPlease check your API key, plan, and billing details on the OpenAI platform.", e))
        except Exception as e:
            # This will catch other potential API errors (network, auth, etc.)
            _logger.error("An error occurred during the AI API call: %s", str(e))
            raise UserError(_("An error occurred while contacting the AI service: %s", e))

    def _get_prompt(self):
        position_label = self.position

        prompt_parts = [
            f"Please act as a compliance research expert. Find a list of individuals who held the position of '{position_label}' in the country '{self.country_id.name}' during the period {self.year}.",
            "\nProvide the response as a single, clean JSON object with a key 'peps', which is an array of objects. Each object must have the following keys:",
            '- "name": (string) The full name of the person.',
            '- "specific_title": (string) Their specific title or role during that period (e.g., "Prime Minister", "Minister of Finance").',
            '- "start_year": (integer) The year the person started this specific position.',
            '- "end_year": (integer or null) The year the person ended this specific position. If they are still in the position, return null.',
            '- "birth_year": (integer or null) The year of birth of the person. Return null if not found.',
            '- "notes": (string) A brief note about their tenure or significance.',
            "\nCRITICAL FORMATTING RULE FOR 'name' FIELD:",
            "If the country is Mongolia, the name MUST be in the format 'Эцэг/эхийн нэр Өөрийн нэр (Firstname Surname)'.",
            "You must expand any initials. For example:",
            "  - If you find 'Д. Ганзориг (D. Ganzorig)', you must research and return the full name like 'Дамдин Ганзориг (Ganzorig Damdin)'.",
            "  - If you find 'Ухнаа Хүрэлсүх (Khurelsukh Ukhnaa)', this format is correct.",
            "For all other countries, provide the name as commonly written.",
            "\nIf you cannot find any information, return a JSON object with an empty 'peps' array."
        ]
        return "\n".join(prompt_parts)

    def _search_with_gemini(self):
        if not genai:
            raise UserError(_("The 'google-generativeai' library is not installed. Please install it using: pip install google-generativeai"))

        api_key = self.env['ir.config_parameter'].sudo().get_param('pep_checker.google_api_key')
        if not api_key:
            raise UserError(_("Google AI API key is not configured. Please set 'pep_checker.google_api_key' in System Parameters."))

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(self.ai_model)
        prompt = self._get_prompt()

        _logger.info("Sending prompt to Gemini API (%s) for PEP list search.", self.ai_model)
        response = model.generate_content(prompt)
        return response.text

    def _search_with_openai(self):
        if not openai:
            raise UserError(_("The 'openai' library is not installed. Please install it using: pip install openai"))

        api_key = self.env['ir.config_parameter'].sudo().get_param('pep_checker.openai_api_key')
        if not api_key:
            raise UserError(_("OpenAI API key is not configured. Please set 'pep_checker.openai_api_key' in System Parameters."))

        client = openai.OpenAI(api_key=api_key)
        prompt = self._get_prompt()

        _logger.info("Sending prompt to OpenAI API (%s) for PEP list search.", self.ai_model)
        
        # OpenAI's chat completions API expects a list of messages
        messages = [
            {"role": "system", "content": "You are a helpful compliance research expert that provides responses in JSON format."},
            {"role": "user", "content": prompt}
        ]

        response = client.chat.completions.create(
            model=self.ai_model,
            messages=messages,
            response_format={"type": "json_object"}, # Enforce JSON output
        )
        return response.choices[0].message.content

    def _process_ai_response(self, response_text):
        # Clean the response to handle potential markdown code blocks
        if response_text:
            response_text = response_text.strip().replace('```json', '').replace('```', '').strip()
        else:
            raise ValueError("Received an empty response from the AI.")

        result_data = json.loads(response_text)
        _logger.info("Received AI response for PEP list search: %s", result_data)

        peps = result_data.get('peps', [])
        if peps:
            vals_list = [{
                'name': pep.get('name'),
                'specific_title': pep.get('specific_title'),
                'notes': pep.get('notes'),
                'start_year': str(pep.get('start_year')) if pep.get('start_year') else False,
                'end_year': str(pep.get('end_year')) if pep.get('end_year') else False,
                'birth_year': str(pep.get('birth_year')) if pep.get('birth_year') else False,
            } for pep in peps]
            self.result_line_ids = [(0, 0, vals) for vals in vals_list]
        else:
            self.message_post(body=_("No individuals found for the specified criteria."))

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'pep.ai.search.wizard',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
        }