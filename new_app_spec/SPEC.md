# Feature Specification — PEP Compliance Manager

## 1. PEP Person Management

### 1.1 Core Fields

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `id` | UUID / Serial | auto | auto | Primary key |
| `name` | String(255) | Yes | — | Full name of the PEP |
| `name_phonetic` | String(255) | Computed | — | Metaphone phonetic encoding of name (for fuzzy search) |
| `date_of_birth` | Date | No | — | Date of birth |
| `nationality` | FK → Country | No | — | Country of nationality |
| `position` | Enum | Yes | — | Position category (see 1.2) |
| `custom_position` | String(255) | Conditional | — | Required when position = 'other' |
| `organization` | String(255) | Yes | — | Organization/institution name |
| `organization_type` | Enum | No | — | Organization classification (see 1.3) |
| `pep_type` | Enum | Computed | — | Domestic / Foreign / International (see 1.4) |
| `status` | Enum | No | 'active' | active / former / deceased |
| `start_date` | Integer | No | — | Position start year |
| `end_date` | Integer | No | — | Position end year |
| `risk_level` | Enum | Computed | — | low / medium / high (see 1.5) |
| `source` | Text | No | — | Information source |
| `source_url` | String(500) | No | — | URL to source document |
| `source_date` | Date | No | — | Date source was published |
| `notes` | Text | No | — | Additional notes |
| `self_declared` | Boolean | No | false | Whether person self-declared PEP status |
| `self_declaration_date` | Date | No | — | Date of self-declaration |
| `retention_period` | Integer | No | 5 | Record retention period in years |
| `active` | Boolean | No | true | Soft-delete flag |
| `last_checked` | Datetime | No | now() | Last verification timestamp |
| `created_at` | Datetime | auto | now() | Record creation timestamp |
| `updated_at` | Datetime | auto | now() | Last modification timestamp |
| `created_by` | FK → User | auto | current user | Who created the record |

### 1.2 Position Categories (Enum)

Based on Mongolian Law and FATF Recommendations:

| Value | Label |
|-------|-------|
| `head_state` | Head of State/Government |
| `parliament` | Member of Parliament |
| `governor` | Governor of Province/Capital City |
| `judicial` | Senior Judicial Official |
| `central_bank_board` | Member of Court of Auditors or Board of a Central Bank |
| `diplomat_military` | Ambassador or High-ranking Military Officer |
| `state_enterprise` | Senior State-Owned Enterprise Executive |
| `party_official` | Senior Political Party Official |
| `intl_director` | Director/Deputy Director (International Org) |
| `intl_board` | Board Member (International Org) |
| `intl_senior` | Senior Management (International Org) |
| `other` | Other (Not defined in Mongolian Law) |

### 1.3 Organization Types (Enum)

| Value | Label |
|-------|-------|
| `government` | Government |
| `political_party` | Political Party |
| `judiciary` | Judiciary |
| `military` | Military |
| `state_owned` | State-Owned Enterprise |
| `international_org` | International Organization |
| `other` | Other |

### 1.4 PEP Type Computation

Computed automatically based on:

```python
if organization_type == 'international_org':
    pep_type = 'international'
elif nationality == company_country:
    pep_type = 'domestic'
else:
    pep_type = 'foreign'
```

**Company country** should be configurable via application settings.

### 1.5 Risk Level Computation

Computed automatically:

```python
if status == 'deceased':
    risk_level = 'low'
elif status == 'former':
    if end_date and (current_year - end_date) > 5:
        risk_level = 'low'
    else:
        risk_level = 'medium'
elif pep_type in ('domestic', 'foreign'):
    risk_level = 'high'
elif pep_type == 'international':
    if position in ('intl_director', 'intl_board'):
        risk_level = 'high'
    else:
        risk_level = 'medium'
```

### 1.6 Validation Rules

1. **Unique constraint**: `(name, date_of_birth)` must be unique across all PEP persons
2. **Mongolian name format**: When nationality is Mongolia (country code 'MN'), name must match regex:
   ```
   ^[\u0400-\u04FF\s.\-]+\s\([\w\s.\-]+\)$
   ```
   Example valid: `Ухнаа Хүрэлсүх (Khurelsukh Ukhnaa)`
3. **International PEP consistency**: If `pep_type == 'international'`, then `organization_type` must be `'international_org'`
4. **Custom position required**: If `position == 'other'`, then `custom_position` is required

### 1.7 Phonetic Name Computation

Uses the `jellyfish` library's metaphone algorithm:
```python
name_phonetic = jellyfish.metaphone(name) if name else None
```
Stored and indexed for fast fuzzy searching.

---

## 2. Enhanced Due Diligence (EDD)

### 2.1 EDD Fields on PEP Person

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `edd_status` | Enum | 'pending' | pending / in_progress / completed / review_needed |
| `edd_last_review` | Date | — | Date of last EDD review |
| `edd_next_review` | Date | Computed | Next review date based on frequency |
| `monitoring_frequency` | Enum | 'quarterly' | monthly / quarterly / semi_annual / annual |
| `senior_approval_id` | FK → User | — | Who approved the EDD |
| `senior_approval_date` | Datetime | — | When approval was granted |
| `source_of_wealth` | Text | — | How wealth was acquired |
| `source_of_funds` | Text | — | Origin of funds in business relationship |

### 2.2 Next Review Date Computation

```python
months_map = {
    'monthly': 1,
    'quarterly': 3,
    'semi_annual': 6,
    'annual': 12,
}
if edd_last_review and monitoring_frequency:
    edd_next_review = edd_last_review + relativedelta(months=months_map[monitoring_frequency])
else:
    edd_next_review = today()
```

### 2.3 EDD with xacxom (Web Scraping)

**Trigger**: User clicks "EDD with xacxom" button on a PEP person record.

**Process**:
1. Parse the Cyrillic portion of the PEP name into `last_name` (patronymic) and `first_name` (given name)
2. Make GET request to `{XACXOM_SEARCH_URL}?last_name={}&first_name={}`
3. Parse the HTML response table:
   - Column 2 (index 1): Contains hidden input with `class="aid_number"` → extract `value`
   - Column 3 (index 2): Declaration year
   - Column 4 (index 3): Last name
   - Column 5 (index 4): First name
   - Column 6 (index 5): Organization
   - Column 7 (index 6): Position
4. Update the PEP person record:
   - `last_checked` = now
   - `edd_last_review` = today
   - `source` = 'https://xacxom.iaac.mn'
   - `start_date` = min(declaration_years)
   - `end_date` = max(declaration_years)
   - Append formatted verification summary to `notes`

**Headers for scraping**:
```python
{
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 ...',
    'X-Requested-With': 'XMLHttpRequest',
}
```

**Error handling**: If name doesn't have at least 2 parts when split by space, show error.

### 2.4 Senior Approval Workflow

**Trigger**: User clicks "Request Approval" button (only visible when no approval exists and EDD is not completed).

**Process**:
1. Open modal dialog with fields: Approved By (default: current user), Approval Note
2. On confirm:
   - Set `senior_approval_id` = selected user
   - Set `senior_approval_date` = now
   - Set `edd_status` = 'completed'

### 2.5 Schedule EDD Review

**Trigger**: User clicks "Schedule EDD Review" button.

**Process**: Set `edd_last_review = today()`, which triggers recomputation of `edd_next_review`.

### 2.6 Automated EDD Review Scheduler

A **scheduled background job** (e.g., daily cron) that:
1. Finds all PEP persons where:
   - `risk_level == 'high'`
   - `edd_next_review <= today`
   - `status == 'active'`
   - `edd_status != 'review_needed'`
2. For each: sets `edd_status = 'review_needed'` and creates a notification/task for managers

---

## 3. PEP Relationships

### 3.1 Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | UUID / Serial | auto | Primary key |
| `name` | String(255) | Yes | Name of the related person |
| `pep_id` | FK → PEPPerson | Yes | The PEP this person is related to (cascade delete) |
| `relationship_type` | Enum | Yes | 'family' or 'associate' |
| `family_relation` | Enum | Conditional | Required if type='family' (see 3.2) |
| `association_type` | Enum | Conditional | Required if type='associate' (see 3.3) |
| `date_of_birth` | Date | No | |
| `nationality` | FK → Country | No | |
| `edd_required` | Boolean | No | true | Whether EDD is needed |
| `source_of_wealth` | Text | No | |
| `source_of_funds` | Text | No | |
| `relationship_notes` | Text | No | |
| `verification_date` | Date | No | |
| `verification_source` | Text | No | |
| `active` | Boolean | No | true | Soft-delete flag |

### 3.2 Family Relation Options

| Value | Label |
|-------|-------|
| `spouse` | Spouse/Partner |
| `child` | Child |
| `child_spouse` | Child's Spouse/Partner |
| `parent` | Parent |
| `sibling` | Sibling |
| `other` | Other Family Member |

### 3.3 Association Type Options

| Value | Label |
|-------|-------|
| `business_partner` | Business Partner |
| `joint_owner` | Joint Beneficial Owner |
| `legal_arrangement` | Legal Arrangement Beneficial Owner |
| `close_business` | Close Business Relationship |
| `other` | Other Association |

### 3.4 Validation Rules

1. If `relationship_type == 'family'`, then `family_relation` is **required**
2. If `relationship_type == 'associate'`, then `association_type` is **required**
3. When changing `relationship_type`, clear both `family_relation` and `association_type`

---

## 4. PEP Screening

### 4.1 Fields

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `id` | UUID / Serial | auto | auto | Primary key |
| `name` | String(255) | Yes | — | Name to screen |
| `date_of_birth` | Date | No | — | |
| `nationality` | FK → Country | No | — | |
| `screening_date` | Datetime | Yes | now() | When screening was performed |
| `screening_type` | Enum | Yes | 'initial' | initial / periodic / trigger / exit |
| `trigger_reason` | Enum | Conditional | — | Required context when type='trigger' (news / transaction / structure / other) |
| `result` | Enum | No | — | match / possible / no_match |
| `matched_pep_id` | FK → PEPPerson | No | — | Linked matched PEP |
| `confidence_score` | Float | No | — | Match confidence percentage |
| `screened_by` | FK → User | Yes | current user | Who performed the screening |
| `screening_method` | Enum | Yes | — | database / media / official / manual / ai_screening |
| `database_used` | Enum | Conditional | — | worldcheck / dowjones / refinitiv / other (only when method='database') |
| `evidence_refs` | Text | No | — | Supporting document references |
| `notes` | Text | No | — | Screening notes |

### 4.2 Screening Workflow (`action_screen_name`)

**Step 1: Internal Database Search**
1. Build search query combining:
   - Text match: `name ILIKE '%{search_term}%'`
   - Phonetic match: `name_phonetic = jellyfish.metaphone(search_term)`
   - These are OR-combined
2. If **exactly 1 match**: Set result='match', link matched_pep_id, method='database'
3. If **multiple matches**: Set result='possible', list names in notes, method='database'
4. If matches found, stop here.

**Step 2: AI Screening (fallback)**
Only if no internal matches found:
1. Build prompt including: name, date_of_birth (if set), nationality (if set)
2. Send to configured AI provider (currently Gemini)
3. Expect JSON response:
   ```json
   {
     "is_pep": true/false,
     "position": "string",
     "country": "string",
     "summary": "string",
     "source_urls": ["url1", "url2"]
   }
   ```
4. If `is_pep == true`: Set result='possible', method='ai_screening', notes=summary, evidence_refs=URLs
5. If `is_pep == false`: Set result='no_match', method='ai_screening', notes=summary

**AI Screening Prompt**:
```
Please act as a compliance expert. Analyze public information for the following individual
to determine if they are a Politically Exposed Person (PEP):
Name: {name}
Date of Birth: {date_of_birth}  [if provided]
Nationality: {nationality}  [if provided]

Based on your analysis, provide a response in JSON format with the following keys:
- "is_pep": (boolean) true if they are a PEP, otherwise false.
- "position": (string) The specific political title or role held, if any.
- "country": (string) The country associated with their political role.
- "summary": (string) A brief summary of why they are or are not considered a PEP.
- "source_urls": (array of strings) A list of up to 3 URLs to public sources that support your conclusion.

If you cannot find any information, return a JSON object with 'is_pep' as false and a summary
explaining that no definitive information was found.
```

### 4.3 Access Rules

- **Users**: Can only see screenings where `screened_by == current_user`
- **Managers**: Can see all screenings

---

## 5. AI PEP List Search (Wizard)

### 5.1 Input Fields

| Field | Type | Required | Default |
|-------|------|----------|---------|
| `country_id` | FK → Country | Yes | App's default country |
| `position` | String | Yes | — |
| `year` | String | Yes | 'current' |
| `ai_provider` | Enum | Yes | 'gemini' |
| `ai_model` | String | Yes | Provider default |

### 5.2 Workflow

1. User fills in country, position, year, AI provider
2. On "Search with AI": send prompt to selected AI provider
3. AI returns JSON with `peps` array
4. Display results in a table with columns: Name, Specific Title, Start Year, End Year, Birth Year, Notes
5. Each row has a "Create PEP" button (disabled after creation)

### 5.3 Prompt Template (PEP List Search)

```
Please act as a compliance research expert. Find a list of individuals who held the
position of '{position}' in the country '{country_name}' during the period {year}.

Provide the response as a single, clean JSON object with a key 'peps', which is an array
of objects. Each object must have the following keys:
- "name": (string) The full name of the person.
- "specific_title": (string) Their specific title or role during that period.
- "start_year": (integer) The year the person started this specific position.
- "end_year": (integer or null) The year the person ended this specific position.
- "birth_year": (integer or null) The year of birth of the person.
- "notes": (string) A brief note about their tenure or significance.

CRITICAL FORMATTING RULE FOR 'name' FIELD:
If the country is Mongolia, the name MUST be in the format
'Эцэг/эхийн нэр Өөрийн нэр (Firstname Surname)'.
You must expand any initials.

If you cannot find any information, return a JSON object with an empty 'peps' array.
```

### 5.4 AI Response Schema

```json
{
  "peps": [
    {
      "name": "string",
      "specific_title": "string",
      "start_year": 2020,
      "end_year": null,
      "birth_year": 1965,
      "notes": "string"
    }
  ]
}
```

### 5.5 "Create PEP" from Result

For each result line, creating a PEP person:
1. Check for duplicates: search by exact name OR transliterated name (part in parentheses)
2. If duplicate found, show error
3. Create PEP person with:
   - `name` = result name
   - `position` = 'other' (AI provides free text, not enum)
   - `custom_position` = result specific_title
   - `organization` = "Government of {country}"
   - `nationality` = selected country
   - `notes` = result notes
   - `source` = "AI Search for '{position}' in {country} ({year})"
   - `start_date` = result start_year
   - `end_date` = result end_year
   - `date_of_birth` = January 1 of birth_year (if provided)

---

## 6. AI Position Search (Wizard)

### 6.1 Input Fields

| Field | Type | Required | Default |
|-------|------|----------|---------|
| `country_id` | FK → Country | Yes | App's default country |
| `year` | String | Yes | Current year |
| `ai_provider` | Enum | Yes | 'gemini' |
| `ai_model` | String | Yes | Provider default |

### 6.2 Workflow

1. User fills in country, year, AI provider
2. On "Search": send prompt to AI
3. Display results: Position Title, Suggested Category (from position enum), Notes
4. Each row has "Register" button to create a Position Template

### 6.3 Prompt Template (Position Search)

```
Please act as a legal and compliance expert specializing in AML regulations.

Your task is to identify key PEP positions for the country of '{country_name}' for the year {year}.

Provide the response as a single, clean JSON object with a key 'positions', which is an array
of objects. Each object must have the following keys:
- "position_title": (string) The specific, official title of the position.
- "category": (string) One of: {valid_categories}
- "notes": (string) A brief explanation of why this position is considered a PEP role.

Focus on the most senior and influential roles in the executive, legislative, judicial,
military, and state-owned enterprise sectors.

If you cannot find any information, return a JSON object with an empty 'positions' array.
```

### 6.4 AI Response Schema

```json
{
  "positions": [
    {
      "position_title": "Minister of Finance",
      "category": "head_state",
      "notes": "Controls national budget allocation"
    }
  ]
}
```

### 6.5 "Register" from Result

1. Check for duplicate: same title + country + year
2. If duplicate, show error
3. Create Position Template record

---

## 7. Position Templates

### 7.1 Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | UUID / Serial | auto | Primary key |
| `name` | String(255) | Yes | Position title |
| `category` | Enum | Yes | One of the position categories (1.2) |
| `country_id` | FK → Country | No | |
| `year` | String | No | Year or period |
| `notes` | Text | No | |
| `active` | Boolean | No | true |

### 7.2 Constraints

- **Unique**: `(name, country_id, year)` must be unique

---

## 8. Web Scraper (Bulk)

### 8.1 Input Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `max_pages` | Integer | 1 | Pages to scrape (0 = all) |

### 8.2 Workflow

1. User enters max_pages and clicks "Start Scraping"
2. Job is queued as a background task
3. For each page (1..max_pages):
   - GET `{XACXOM_SEARCH_URL}?page={n}`
   - Parse HTML table (same column mapping as EDD scraping in section 2.3)
   - Collect: name, position, organization, declaration_year, aid_number
4. On completion, send notification to user with record count
5. Results are displayed in the wizard if still open

### 8.3 Scraper Result Fields

| Field | Type | Description |
|-------|------|-------------|
| `name` | String | Full name (last + first) |
| `position` | String | Position title |
| `organization` | String | Organization name |
| `declaration_year` | String | Year of declaration |
| `aid_number` | String | Internal ID for AJAX detail lookups |

---

## 9. AI Provider Integration

### 9.1 Shared Interface

Both Gemini and OpenAI must be callable through the same abstraction:

```python
class AIProvider(ABC):
    def search(self, prompt: str, model: str) -> str:
        """Send prompt and return raw JSON string response"""
```

### 9.2 Gemini Implementation

```python
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel(model_name)
response = model.generate_content(
    prompt,
    generation_config=genai.types.GenerationConfig(response_mime_type="application/json")
)
return response.text
```

### 9.3 OpenAI Implementation

```python
client = openai.OpenAI(api_key=OPENAI_API_KEY)
response = client.chat.completions.create(
    model=model_name,
    messages=[
        {"role": "system", "content": "You are a helpful compliance research expert that provides responses in JSON format."},
        {"role": "user", "content": prompt}
    ],
    response_format={"type": "json_object"},
)
return response.choices[0].message.content
```

### 9.4 Default Models

| Provider | Default Model | Config Key |
|----------|--------------|------------|
| Gemini | `gemini-2.5-flash` | `GEMINI_MODEL` |
| OpenAI | `gpt-4o` | `OPENAI_MODEL` |

### 9.5 JSON Response Cleaning

AI responses may be wrapped in markdown code blocks. Always strip:
```python
response_text = response_text.strip().replace('```json', '').replace('```', '').strip()
```

---

## 10. Authentication and Authorization

### 10.1 Roles

| Role | Permissions |
|------|------------|
| **User** (`user`) | Read, Write, Create on all models. No delete on PEP Person, Relationship, Screening, Position Template. Full CRUD on wizard/transient data. Can only see own screenings. |
| **Manager** (`manager`) | Full CRUD on all models. Can see all screenings. Inherits all User permissions. |

### 10.2 Record-Level Rules

- **PEP Persons**: All users can read/write/create. Only managers can delete.
- **Screenings**: Users see only records where `screened_by == current_user`. Managers see all.
- **Relationships**: All users can read/write/create. Only managers can delete.
- **Position Templates**: Users can read and create. Managers have full CRUD.

---

## 11. Audit Trail

Every change to PEP Person, Relationship, and Screening records must be logged:

| Field | Description |
|-------|-------------|
| `entity_type` | Which model was changed |
| `entity_id` | ID of the changed record |
| `user_id` | Who made the change |
| `timestamp` | When |
| `field_name` | Which field changed |
| `old_value` | Previous value (as string) |
| `new_value` | New value (as string) |

**Tracked fields on PEP Person**: name, nationality, position, custom_position, organization, organization_type, pep_type, status, risk_level, edd_status, monitoring_frequency, source_of_wealth, source_of_funds, senior_approval_id, self_declared, notes

**Tracked fields on Relationship**: name, relationship_type, source_of_wealth, source_of_funds, verification_date, verification_source

**Tracked fields on Screening**: result, screening_type, screening_method

---

## 12. Countries Reference Data

The application needs a `country` reference table with at minimum:
- `id` (primary key)
- `name` (e.g., "Mongolia")
- `code` (ISO 3166-1 alpha-2, e.g., "MN")

Pre-populate with all ISO countries. The Mongolian name format validation depends on `code == 'MN'`.
