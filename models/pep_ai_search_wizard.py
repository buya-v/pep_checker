from odoo import models, fields, api, _
from odoo.exceptions import UserError
import json
import logging

try:
    import google.generativeai as genai
except ImportError:
    genai = None

_logger = logging.getLogger(__name__)

class PEPAISearchWizard(models.TransientModel):
    _name = 'pep.ai.search.wizard'
    _description = 'PEP AI Search Wizard'

    country_id = fields.Many2one('res.country', string='Country', required=True, default=lambda self: self.env.company.country_id)
    position = fields.Char(string='Position/Role', required=True, help="Enter a specific role, e.g., 'Minister of Finance', 'Central Bank Governor'.")
    year = fields.Char(string='Year / Period', required=True, default='current', help="Enter a year (e.g., 2024), a range (e.g., 2020-2024), or a term (e.g., 'current').")
    result_line_ids = fields.One2many('pep.ai.search.result.line', 'wizard_id', string='Search Results')

    def action_search_pep_with_ai(self):
        self.ensure_one()

        if not genai:
            raise UserError(_("The 'google-generativeai' library is not installed. Please install it using: pip install google-generativeai"))

        api_key = self.env['ir.config_parameter'].sudo().get_param('pep_checker.google_api_key')
        if not api_key:
            raise UserError(_("Google AI API key is not configured. Please set 'pep_checker.google_api_key' in System Parameters."))

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.5-flash')

        position_label = self.position

        prompt_parts = [
            f"Please act as a compliance research expert. Find a list of individuals who held the position of '{position_label}' in the country '{self.country_id.name}' during the period {self.year}.",
            "\nProvide the response as a single, clean JSON object with a key 'peps', which is an array of objects. Each object must have the following keys:",
            '- "name": (string) The full name of the person.',
            '- "specific_title": (string) Their specific title or role during that year (e.g., "Prime Minister", "Minister of Finance").',
            '- "notes": (string) A brief note about their tenure or significance.',
            "\nCRITICAL FORMATTING RULE FOR 'name' FIELD:",
            "If the country is Mongolia, the name MUST be in the format 'Эцэг/эхийн нэр Өөрийн нэр (Firstname Surname)'.",
            "You must expand any initials. For example:",
            "  - If you find 'Д. Ганзориг (D. Ganzorig)', you must research and return the full name like 'Дамдин Ганзориг (Ganzorig Damdin)'.",
            "  - If you find 'Ухнаа Хүрэлсүх (Khurelsukh Ukhnaa)', this format is correct.",
            "For all other countries, provide the name as commonly written.",
            "\nIf you cannot find any information, return a JSON object with an empty 'peps' array."
        ]
        prompt = "\n".join(prompt_parts)

        try:
            _logger.info("Sending prompt to Gemini API for PEP list search. Country: %s, Position: %s, Year: %s", self.country_id.name, position_label, self.year)
            response = model.generate_content(prompt)
            
            response_text = response.text.strip().replace('```json', '').replace('```', '').strip()
            result_data = json.loads(response_text)
            _logger.info("Received AI response for PEP list search: %s", result_data)

            # Clear previous results
            self.result_line_ids.unlink()

            peps = result_data.get('peps', [])
            if peps:
                vals_list = []
                for pep in peps:
                    vals_list.append({
                        'name': pep.get('name'),
                        'specific_title': pep.get('specific_title'),
                        'notes': pep.get('notes'),
                    })
                self.result_line_ids = [(0, 0, vals) for vals in vals_list]
            else:
                self.message_post(body=_("No individuals found for the specified criteria."))
        except json.JSONDecodeError:
            _logger.error("Failed to decode JSON from AI response: %s", response.text)
            raise UserError(_("The AI returned a response that could not be processed as JSON. Please try again or check the logs for the raw response."))
        except Exception as e:
            _logger.error("An error occurred during AI PEP search: %s", str(e))
            raise UserError(_("An error occurred while contacting the AI service: %s", e))

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'pep.ai.search.wizard',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
        }