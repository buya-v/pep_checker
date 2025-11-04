from odoo import models, fields, api, _
from odoo.exceptions import UserError
import json
import logging

try:
    import openai
except ImportError:
    openai = None

_logger = logging.getLogger(__name__)

class PEPAISearchWizard(models.TransientModel):
    _name = 'pep.ai.search.wizard'
    _inherit = ['pep.ai.mixin']
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
        if self.ai_provider:
            self.ai_model = self._get_default_ai_model(self.ai_provider)
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
        """Renders the AI prompt from an XML template."""
        return self.env['ir.qweb']._render('pep_checker.ai_pep_list_search_prompt', {
            'position': self.position,
            'country_name': self.country_id.name,
            'year': self.year,
        })

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