from odoo import models, fields, api, _
from odoo.exceptions import UserError
import json
import logging

_logger = logging.getLogger(__name__)

class PEPPositionAISearchWizard(models.TransientModel):
    _name = 'pep.position.ai.search.wizard'
    _inherit = ['pep.ai.mixin']
    _description = 'PEP Position AI Search Wizard'

    country_id = fields.Many2one('res.country', string='Country', required=True, default=lambda self: self.env.company.country_id)
    year = fields.Char(string='Year / Period', required=True, default=lambda self: str(fields.Date.today().year), help="The year for which to find relevant positions (e.g., 2024).")
    ai_provider = fields.Selection([
        ('gemini', 'Google Gemini'),
        ('openai', 'OpenAI ChatGPT')
    ], string='AI Provider', default='gemini', required=True)
    ai_model = fields.Char(string='AI Model', required=True)
    result_line_ids = fields.One2many('pep.position.ai.search.result.line', 'wizard_id', string='Search Results')
    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if 'ai_provider' in res and not res.get('ai_model'):
            res['ai_model'] = self._get_default_ai_model(res['ai_provider'])
        return res

    @api.onchange('ai_provider')
    def _onchange_ai_provider(self):
        if self.ai_provider:
            self.ai_model = self._get_default_ai_model(self.ai_provider)
        else:
            self.ai_model = False

    def action_search_positions_with_ai(self):
        self.ensure_one()
        self.result_line_ids.unlink()
        try:
            response_text = ""
            if self.ai_provider == 'gemini':
                response_text = self._search_with_gemini()
            elif self.ai_provider == 'openai':
                response_text = self._search_with_openai()

            return self._process_ai_response(response_text)
        except Exception as e:
            _logger.error("An error occurred during the AI position search: %s", str(e))
            raise UserError(_("An error occurred while contacting the AI service: %s", e))

    def _get_prompt(self):
        """Renders the AI prompt for position search from an XML template."""
        pep_person_model = self.env['pep.person']
        position_selections = pep_person_model.fields_get(['position'])['position']['selection']
        valid_categories = [key for key, label in position_selections]

        return self.env['ir.qweb']._render('pep_checker.ai_pep_position_search_prompt', {
            'country_name': self.country_id.name,
            'year': self.year,
            'valid_categories': valid_categories,
        })

    def _process_ai_response(self, response_text):
        if response_text:
            response_text = response_text.strip().replace('```json', '').replace('```', '').strip()
        else:
            raise ValueError("Received an empty response from the AI.")

        result_data = json.loads(response_text)
        _logger.info("Received AI response for PEP position search: %s", result_data)

        positions = result_data.get('positions', [])
        if positions:
            vals_list = [{
                'position_title': pos.get('position_title'),
                'suggested_category': pos.get('category'),
                'notes': pos.get('notes'),
            } for pos in positions]
            self.result_line_ids = [(0, 0, vals) for vals in vals_list]
        else:
            self.message_post(body=_("The AI did not find any specific PEP positions for the criteria."))

        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
        }


class PEPPositionAISearchResultLine(models.TransientModel):
    _name = 'pep.position.ai.search.result.line'
    _description = 'PEP Position AI Search Result Line'

    wizard_id = fields.Many2one('pep.position.ai.search.wizard', string='Wizard', ondelete='cascade')
    position_title = fields.Char(string='Position Title', readonly=True)
    suggested_category = fields.Selection(
        string='Suggested Category',
        selection=lambda self: self.env['pep.person']._fields['position'].selection,
        readonly=True
    )
    notes = fields.Text(string='Notes', readonly=True)
    is_registered = fields.Boolean(string="Registered", default=False)

    def action_register_position(self):
        self.ensure_one()
        PositionTemplate = self.env['pep.position.template']

        # Check for duplicates before creating
        existing = PositionTemplate.search([
            ('name', '=ilike', self.position_title),
            ('country_id', '=', self.wizard_id.country_id.id),
            ('year', '=', self.wizard_id.year),
        ], limit=1)

        if existing:
            raise UserError(_("A position template with this title ('%s') already exists for this country and year.", self.position_title))

        PositionTemplate.create({
            'name': self.position_title,
            'category': self.suggested_category,
            'country_id': self.wizard_id.country_id.id,
            'year': self.wizard_id.year,
            'notes': self.notes,
        })

        self.is_registered = True
        return True