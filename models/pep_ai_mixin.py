from odoo import models, api, _
from odoo.exceptions import UserError
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

class PEPAIMixin(models.AbstractModel):
    _name = 'pep.ai.mixin'
    _description = 'PEP AI Search Mixin'

    def _search_with_gemini(self):
        """Shared method to perform a search with the Gemini API."""
        self.ensure_one()
        if not genai:
            raise UserError(_("The 'google-generativeai' library is not installed. Please install it using: pip install google-generativeai"))

        api_key = self.env['ir.config_parameter'].sudo().get_param('pep_checker.google_api_key')
        if not api_key:
            raise UserError(_("Google AI API key is not configured. Please set 'pep_checker.google_api_key' in System Parameters."))

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(self.ai_model)
        prompt = self._get_prompt()

        _logger.info("Sending prompt to Gemini API (%s).", self.ai_model)
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(response_mime_type="application/json")
        )
        return response.text

    def _search_with_openai(self):
        """Shared method to perform a search with the OpenAI API."""
        self.ensure_one()
        if not openai:
            raise UserError(_("The 'openai' library is not installed. Please install it using: pip install openai"))

        api_key = self.env['ir.config_parameter'].sudo().get_param('pep_checker.openai_api_key')
        if not api_key:
            raise UserError(_("OpenAI API key is not configured. Please set 'pep_checker.openai_api_key' in System Parameters."))

        client = openai.OpenAI(api_key=api_key)
        prompt = self._get_prompt()

        _logger.info("Sending prompt to OpenAI API (%s).", self.ai_model)

        messages = [
            {"role": "system", "content": "You are a helpful compliance research expert that provides responses in JSON format."},
            {"role": "user", "content": prompt}
        ]

        response = client.chat.completions.create(
            model=self.ai_model,
            messages=messages,
            response_format={"type": "json_object"},
        )
        return response.choices[0].message.content

    def _get_default_ai_model(self, provider):
        """Shared method to get the default AI model from system parameters."""
        params = self.env['ir.config_parameter'].sudo()
        if provider == 'gemini':
            return params.get_param('pep_checker.gemini_model', 'gemini-2.5-flash')
        if provider == 'openai':
            return params.get_param('pep_checker.openai_model', 'gpt-4o')
        return False