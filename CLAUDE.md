# CLAUDE.md - PEP Checker Module

## Project Overview

PEP Checker is an **Odoo 18.0 module** for managing Politically Exposed Persons (PEPs) as part of AML/KYC compliance. It provides PEP database management, AI-powered screening (Google Gemini & OpenAI), web scraping from official Mongolian sources, and Enhanced Due Diligence (EDD) workflows with approval processes.

- **Module technical name:** `pep_checker`
- **Version:** 18.0.1.0.0
- **License:** LGPL-3
- **Framework:** Odoo 18.0 (Python)

## Repository Structure

```
pep_checker/
├── __manifest__.py              # Module manifest (dependencies, data files, metadata)
├── __init__.py                  # Root init (imports models/)
├── models/                      # Core business logic
│   ├── __init__.py              # Model imports
│   ├── pep.py                   # Main models: pep.person, pep.relationship, pep.screening
│   ├── pep_ai_mixin.py          # Abstract model: shared Gemini & OpenAI integration
│   ├── pep_ai_search_wizard.py  # Transient: AI-powered PEP list discovery
│   ├── pep_ai_search_result_line.py  # Transient: search result lines
│   ├── pep_position_template.py      # Model: reusable position definitions
│   ├── pep_position_ai_search_wizard.py  # Transient: find PEP positions by country
│   └── pep_web_scraper_wizard.py     # Transient: background scraping from xacxom.iaac.mn
├── views/                       # XML view definitions (forms, trees, search, actions)
│   ├── pep_views.xml            # Main PEP person/screening/relationship views
│   ├── pep_position_template_views.xml
│   ├── pep_position_ai_search_views.xml
│   └── views.xml                # Top-level menu structure
├── data/                        # Data files loaded on install
│   ├── ai_prompts.xml           # AI prompt templates (rendered via ir.qweb)
│   ├── data.xml                 # Sample PEP data
│   └── mn_data.xml              # Mongolia-specific PEP data (Cyrillic names)
├── security/                    # Access control
│   ├── pep_security.xml         # Security groups (group_pep_user, group_pep_manager)
│   └── ir.model.access.csv      # Model-level CRUD permissions
├── tests/                       # Test suite
│   └── test_pep.py              # Unit tests (TransactionCase)
└── demo/                        # Deprecated (data moved to data/)
    └── demo.xml
```

## Key Models

| Model | Type | File | Purpose |
|-------|------|------|---------|
| `pep.person` | `models.Model` | `models/pep.py` | Main PEP registry (name, DOB, positions, risk level) |
| `pep.relationship` | `models.Model` | `models/pep.py` | Family members and close associates |
| `pep.screening` | `models.Model` | `models/pep.py` | Name screening records with match results |
| `pep.position.template` | `models.Model` | `models/pep_position_template.py` | Reusable position definitions by country/year |
| `pep.ai.mixin` | `models.AbstractModel` | `models/pep_ai_mixin.py` | Shared AI provider integration (Gemini + OpenAI) |
| `pep.ai.search.wizard` | `models.TransientModel` | `models/pep_ai_search_wizard.py` | Interactive PEP discovery via AI |
| `pep.position.ai.search.wizard` | `models.TransientModel` | `models/pep_position_ai_search_wizard.py` | Find key PEP positions by country |
| `pep.web.scraper.wizard` | `models.TransientModel` | `models/pep_web_scraper_wizard.py` | Background scraping from xacxom.iaac.mn |

### Model Relationships

```
pep.person (main)
├── pep.relationship (One2many: family_members_ids, close_associates_ids)
├── pep.screening (inverse relation via matched_pep_id)
└── pep.position.template (Many2one via nationality + year)
```

## Development Setup

### Dependencies

**Odoo module dependencies** (in `__manifest__.py`):
- `base` - Core Odoo
- `mail` - Chatter and activity tracking
- `queue_job` - Background job processing for async scraping

**External Python dependencies:**
- `google-generativeai` - Google Gemini API
- `openai` - OpenAI API
- `requests` - HTTP for web scraping
- `beautifulsoup4` - HTML parsing
- `jellyfish` - Phonetic/fuzzy name matching
- `dateutil` - Date utilities

All external libraries are imported with try/except — the module loads even if dependencies are missing, but related features will raise user-friendly errors.

### Running Tests

```bash
# Run module tests via Odoo's test runner
odoo -d <database_name> -i pep_checker --test-enable --stop-after-init
```

Tests use `odoo.tests.common.TransactionCase`. Test files are in `tests/` with `at_install = False` and `post_install = True`.

### Configuration (System Parameters)

These are set in Odoo Settings > Technical > Parameters:

| Parameter | Purpose | Default |
|-----------|---------|---------|
| `pep_checker.google_api_key` | Gemini API key | *(required for AI features)* |
| `pep_checker.openai_api_key` | OpenAI API key | *(required for AI features)* |
| `pep_checker.gemini_model` | Gemini model name | `gemini-2.5-flash` |
| `pep_checker.openai_model` | OpenAI model name | `gpt-4o` |
| `pep_checker.xacxom_search_url` | Scraping endpoint | `https://xacxom.iaac.mn/xacxom/search` |

## Coding Conventions

### Naming

- **Model names:** `pep.<entity>` (e.g., `pep.person`, `pep.screening`)
- **Transient models:** Same pattern for wizards (e.g., `pep.ai.search.wizard`)
- **Fields:** `snake_case` (e.g., `date_of_birth`, `source_of_wealth`, `edd_status`)
- **Computed methods:** `_compute_<field_name>` (e.g., `_compute_risk_level`)
- **Action methods:** `action_<verb>` (e.g., `action_screen_name`, `action_edd_with_xacxom`)
- **Private methods:** Prefixed with `_` (e.g., `_get_prompt`, `_search_with_gemini`)
- **XML IDs:** `view_<model>_<type>` for views, `action_<model>` for actions
- **Constants:** `UPPER_CASE` (e.g., `HEADERS` dict for web scraping)

### Odoo Patterns Used

- **Mixin pattern** for reusable AI logic (`pep.ai.mixin` as `AbstractModel`)
- **Transient models** for multi-step wizard workflows
- **`@api.depends`** for computed fields with proper dependency tracking
- **`@api.constrains`** for business rule validation
- **`_sql_constraints`** for database-level integrity (unique name+DOB, unique position template)
- **`ir.qweb` template rendering** for AI prompt construction from XML templates
- **Logging** via `logging.getLogger(__name__)` in each file

### Security Model

Two groups defined in `security/pep_security.xml`:
- **`group_pep_user`** — Read, write, create (no delete on core models)
- **`group_pep_manager`** — Full CRUD including delete

Record rules restrict screening visibility: users see only their own screenings; managers see all.

## Key Workflows

1. **AI PEP List Search** — `pep.ai.search.wizard` → calls Gemini/OpenAI → returns result lines → creates `pep.person` records
2. **Name Screening** — `pep.screening` → `action_screen_name()` → fuzzy match against DB (jellyfish phonetic) → falls back to AI
3. **EDD with xacxom** — `pep.person` → `action_edd_with_xacxom()` → web scrapes official Mongolian source → updates person record
4. **Senior Approval** — `pep.approval.wizard` → `action_confirm_approval()` → marks EDD as completed

## Common Tasks

### Adding a New Field to pep.person

1. Add the field definition in `models/pep.py` under the `PEPPerson` class
2. Add the field to the appropriate view in `views/pep_views.xml`
3. If it needs access control, update `security/ir.model.access.csv`

### Adding a New Wizard

1. Create a new file in `models/` (e.g., `pep_new_wizard.py`)
2. Import it in `models/__init__.py`
3. Create corresponding views in `views/`
4. Register the view XML in `__manifest__.py` under `'data'`
5. Add access rules in `security/ir.model.access.csv`

### Adding AI Prompt Templates

Prompts are defined as `ir.ui.view` QWeb templates in `data/ai_prompts.xml`. They are rendered with variable substitution via `self.env['ir.qweb']._render()`.

## Important Notes

- **No CI/CD pipeline** — No GitHub Actions or other CI configured. Run tests locally.
- **No linter configuration** — No pylintrc, flake8, or ruff config. Follow existing code style.
- **Graceful degradation** — All external library imports are wrapped in try/except. Check import availability before calling AI/scraping features.
- **Mongolia-specific data** — `data/mn_data.xml` contains Cyrillic names. Handle Unicode properly.
- **demo/ is deprecated** — Sample data has been moved to `data/data.xml`. Do not add new data to `demo/`.
