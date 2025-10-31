from odoo import models, fields, api, _
from odoo.exceptions import UserError
import re

class PEPAISearchResultLine(models.TransientModel):
    _name = 'pep.ai.search.result.line'
    _description = 'PEP AI Search Result Line'

    wizard_id = fields.Many2one('pep.ai.search.wizard', string='Wizard', ondelete='cascade')
    name = fields.Char(string='Name', readonly=True)
    specific_title = fields.Char(string='Specific Title', readonly=True)
    notes = fields.Text(string='Notes', readonly=True)
    is_created = fields.Boolean(string="PEP Created", default=False)

    def action_create_pep_person(self):
        self.ensure_one()

        # More robust duplicate check for names like "Original (Transliteration)"
        search_name = self.name
        search_domain = [('name', '=ilike', search_name)]

        # Extract the part in parentheses to also check for the transliterated name
        match = re.search(r'\((.*?)\)', search_name)
        if match:
            transliterated_name = match.group(1).strip()
            # Search for the full name OR the transliterated name
            search_domain = ['|', ('name', '=ilike', search_name), ('name', 'ilike', transliterated_name)]

        existing_pep = self.env['pep.person'].search(search_domain, limit=1)
        if existing_pep:
            raise UserError(_("A PEP with a similar name ('%s') already exists in the database.", existing_pep.name))

        pep_vals = {
            'name': self.name,
            'position': 'other', # Default to 'other' as AI provides free text
            'custom_position': self.specific_title,
            'organization': f"Government of {self.wizard_id.country_id.name}", # A sensible default
            'nationality': self.wizard_id.country_id.id,
            'notes': self.notes,
            'source': f"AI Search for '{self.wizard_id.position}' in {self.wizard_id.country_id.name} ({self.wizard_id.year})",
        }

        # Create the new PEP Person record
        pep_person = self.env['pep.person'].create(pep_vals)

        self.is_created = True

        # Return an action to open the newly created PEP person form
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'pep.person',
            'view_mode': 'form',
            'res_id': pep_person.id,
            'target': 'new', # Open in a new dialog/tab
        }