from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    requests = None
    BeautifulSoup = None

_logger = logging.getLogger(__name__)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'X-Requested-With': 'XMLHttpRequest',
}

class PEPWebScraperWizard(models.TransientModel):
    _name = 'pep.web.scraper.wizard'
    _description = 'PEP Web Scraper Wizard'

    URL = "https://xacxom.iaac.mn/xacxom/search"

    max_pages = fields.Integer(string='Pages to Scrape', default=1, help="Number of pages to scrape from the source website. Set to 0 to scrape all available pages.")
    status = fields.Text(string='Status', readonly=True, default="Ready to start scraping.")
    result_line_ids = fields.One2many('pep.web.scraper.result.line', 'wizard_id', string='Scraped Results')

    def action_start_scraping(self):
        self.ensure_one()

        if not requests or not BeautifulSoup:
            raise UserError(_("The 'requests' and 'beautifulsoup4' libraries are required. Please install them using: pip install requests beautifulsoup4"))

        self.result_line_ids.unlink()
        self.status = "Scraping in progress..."

        scraped_data = []
        page_limit = self.max_pages if self.max_pages > 0 else float('inf')
        current_page = 1

        while current_page <= page_limit:
            page_url = f"{self.URL}?page={current_page}"
            _logger.info("Scraping page: %s", page_url)
            self.status = f"Scraping page {current_page}..."

            try:
                response = requests.get(page_url, headers=HEADERS, timeout=30)
                response.raise_for_status()
            except requests.exceptions.RequestException as e:
                self.status = f"Failed to fetch page {current_page}. Error: {e}"
                _logger.error("Failed to fetch page %s: %s", page_url, e)
                break

            soup = BeautifulSoup(response.content, 'html.parser')
            table = soup.find('table', class_='table')

            if not table:
                self.status = f"No data table found on page {current_page}. Scraping finished."
                _logger.info("No data table found on page %s. Stopping.", page_url)
                break

            rows = table.find_all('tr')
            if len(rows) <= 1: # Only header row
                self.status = f"No data rows found on page {current_page}. Scraping finished."
                _logger.info("No data rows found on page %s. Stopping.", page_url)
                break

            for row in rows[1:]: # Skip header row
                cols = row.find_all('td')
                if len(cols) >= 5:
                    # Corrected column mapping based on HTML sample
                    declaration_year = cols[2].text.strip() if len(cols) > 2 else ''
                    last_name = cols[3].text.strip() if len(cols) > 3 else ''
                    first_name = cols[4].text.strip() if len(cols) > 4 else ''
                    full_name = f"{last_name} {first_name}"
                    organization = cols[5].text.strip() if len(cols) > 5 else ''
                    position = cols[6].text.strip() if len(cols) > 6 else ''
                    # Extract the aid_number from the hidden input in the second column
                    aid_input = cols[1].find('input', class_='aid_number') if len(cols) > 1 else None
                    aid_number = aid_input['value'] if aid_input else ''

                    scraped_data.append({
                        'name': full_name,
                        'position': position,
                        'organization': organization,
                        'declaration_year': declaration_year,
                        'aid_number': aid_number,
                    })
            
            current_page += 1

        if scraped_data:
            self.result_line_ids = [(0, 0, data) for data in scraped_data]
            self.status = f"Scraping complete. Found {len(scraped_data)} records."
        else:
            self.status = "Scraping complete. No new records found."

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'pep.web.scraper.wizard',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
        }

class PEPWebScraperResultLine(models.TransientModel):
    _name = 'pep.web.scraper.result.line'
    _description = 'PEP Web Scraper Result Line'

    wizard_id = fields.Many2one('pep.web.scraper.wizard', string='Wizard', ondelete='cascade')
    name = fields.Char(string='Name', readonly=True)
    position = fields.Char(string='Position', readonly=True)
    organization = fields.Char(string='Organization', readonly=True)
    declaration_year = fields.Char(string='Declaration Year', readonly=True)
    aid_number = fields.Char(string='AID Number', readonly=True, help="The internal ID used for AJAX calls.")
    is_created = fields.Boolean(string="PEP Created", default=False)
    
    # def action_scrape_details(self):
    #     """
    #     TODO: This function is temporarily disabled. It scrapes the detail page
    #     for a specific declaration and displays the results in a new wizard.
    #     """
    #     self.ensure_one()
    #     if not self.aid_number:
    #         raise UserError(_("There is no AID Number available for this entry to fetch details."))

    #     if not requests or not BeautifulSoup:
    #         raise UserError(_("The 'requests' and 'beautifulsoup4' libraries are required. Please install them using: pip install requests beautifulsoup4"))

    #     ajax_url = "https://xacxom.iaac.mn/xacxom/xacxomview"
    #     payload = {'aidNumber': self.aid_number}
    #     _logger.info("Fetching details via AJAX from %s with payload: %s", ajax_url, payload)

    #     try:
    #         response = requests.post(ajax_url, data=payload, headers=HEADERS, timeout=30)
    #         response.raise_for_status()
    #         details_json = response.json()
    #     except requests.exceptions.RequestException as e:
    #         raise UserError(_("Failed to fetch the detail page. Error: %s", e))
    #     except json.JSONDecodeError:
    #         raise UserError(_("The response from the details endpoint was not valid JSON."))

    #     report_details = details_json.get('reportFiveDetail', [])
    #     if not report_details:
    #         raise UserError(_("No details found in the response for this declaration."))

    #     # Format the latest report into a readable summary
    #     latest_report = report_details[-1] # The last item is the most recent
    #     summary_lines = [
    #         f"Declaration Year: {latest_report.get('YEAR', 'N/A')}",
    #         f"Position: {latest_report.get('POSITION_NAME', 'N/A')}",
    #         f"Organization: {latest_report.get('ORG_NAMES', 'N/A')}",
    #         "---",
    #         "INCOME (in MNT thousands):",
    #         f"  - Declarant's Income: {latest_report.get('OWNER_TOTAL', 0):,}",
    #         f"  - Family Member's Income: {latest_report.get('FAMILY_TOTAL', 0):,}",
    #         "---",
    #         "ASSETS (in MNT thousands):",
    #         f"  - Real Estate Value: {latest_report.get('TOTAL_CONSTRUCTION_VALUE', 0):,}",
    #         f"  - Vehicle Value: {latest_report.get('TRANSPORT_TOTAL_VALUE', 0):,}",
    #         f"  - Livestock Value: {latest_report.get('ANIMAL_TOTAL_VALUE', 0):,}",
    #         f"  - Land Value: {latest_report.get('LAND_TOTAL_VALUE', 0):,}",
    #         f"  - Savings & Cash: {latest_report.get('SAVINGS_ALL', 0):,}",
    #         "---",
    #         "LIABILITIES (in MNT thousands):",
    #         f"  - Loan Balance: {latest_report.get('LOAN_TOTAL_BALANCE', 0):,}",
    #         f"  - Receivables Balance: {latest_report.get('RECEIVABLE_BALANCE', 0):,}",
    #     ]
    #     summary = "\n".join(summary_lines)

    #     wizard = self.env['pep.web.scraper.detail.wizard'].create({
    #     'name': self.name,
    #     'summary': summary,
    #     })

    #     return {
    #         'type': 'ir.actions.act_window',
    #         'name': _('Scraped Details'),
    #         'res_model': 'pep.web.scraper.detail.wizard',
    #         'view_mode': 'form',
    #         'res_id': wizard.id,
    #         'target': 'new',
    #     }

class PEPWebScraperDetailWizard(models.TransientModel):
    _name = 'pep.web.scraper.detail.wizard'
    _description = 'PEP Web Scraper Detail Display'

    name = fields.Char(string="Person's Name", readonly=True)
    summary = fields.Text(string="Declaration Summary", readonly=True)