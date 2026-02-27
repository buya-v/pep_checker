# API Specification — PEP Compliance Manager

## Base URL

```
/api/v1
```

## Authentication

All endpoints except `POST /auth/login` and `POST /auth/register` require a valid JWT Bearer token.

```
Authorization: Bearer <jwt_token>
```

### Auth Endpoints

#### `POST /auth/login`

**Request:**
```json
{
  "email": "user@example.com",
  "password": "string"
}
```

**Response (200):**
```json
{
  "access_token": "jwt_string",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "email": "user@example.com",
    "full_name": "John Doe",
    "role": "user"
  }
}
```

**Errors:** 401 (invalid credentials)

#### `POST /auth/register` (Manager only)

**Request:**
```json
{
  "email": "new@example.com",
  "password": "string",
  "full_name": "Jane Doe",
  "role": "user"
}
```

**Response (201):** User object

#### `GET /auth/me`

Returns the current authenticated user.

---

## Standard Response Formats

### Success (single item)
```json
{
  "data": { ... }
}
```

### Success (list with pagination)
```json
{
  "data": [ ... ],
  "total": 150,
  "page": 1,
  "page_size": 25
}
```

### Error
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Human-readable message",
    "details": [ ... ]
  }
}
```

### Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `VALIDATION_ERROR` | 422 | Input validation failed |
| `NOT_FOUND` | 404 | Resource not found |
| `DUPLICATE_ERROR` | 409 | Unique constraint violation |
| `UNAUTHORIZED` | 401 | Not authenticated |
| `FORBIDDEN` | 403 | Insufficient permissions |
| `AI_SERVICE_ERROR` | 502 | AI provider returned an error |
| `SCRAPING_ERROR` | 502 | Web scraping failed |
| `DEPENDENCY_MISSING` | 503 | Required library not available |

---

## PEP Persons

### `GET /pep-persons`

List PEP persons with filtering, searching, and pagination.

**Query Parameters:**

| Param | Type | Description |
|-------|------|-------------|
| `page` | int | Page number (default: 1) |
| `page_size` | int | Items per page (default: 25, max: 100) |
| `search` | string | Text search on name (ILIKE + phonetic) |
| `pep_type` | string | Filter by pep_type |
| `status` | string | Filter by status |
| `risk_level` | string | Filter by risk_level |
| `nationality_id` | int | Filter by nationality |
| `position` | string | Filter by position |
| `active` | bool | Filter by active flag (default: true) |
| `sort_by` | string | Column to sort by (default: name) |
| `sort_order` | string | 'asc' or 'desc' (default: asc) |

**Response (200):** Paginated list of PEP Person objects.

### `GET /pep-persons/{id}`

Get a single PEP person with all relationships loaded.

**Response (200):**
```json
{
  "data": {
    "id": 1,
    "name": "Ухнаа Хүрэлсүх (Khurelsukh Ukhnaa)",
    "name_phonetic": "XRLSX",
    "date_of_birth": "1968-06-14",
    "nationality": { "id": 143, "name": "Mongolia", "code": "MN" },
    "position": "head_state",
    "custom_position": null,
    "organization": "Government of Mongolia",
    "organization_type": "government",
    "pep_type": "domestic",
    "status": "active",
    "start_date": 2021,
    "end_date": null,
    "risk_level": "high",
    "edd_status": "completed",
    "edd_last_review": "2025-01-15",
    "edd_next_review": "2025-04-15",
    "monitoring_frequency": "quarterly",
    "senior_approval_id": 2,
    "senior_approval_date": "2025-01-15T10:00:00Z",
    "source_of_wealth": "...",
    "source_of_funds": "...",
    "source": "https://xacxom.iaac.mn",
    "source_url": null,
    "source_date": null,
    "notes": "...",
    "self_declared": false,
    "self_declaration_date": null,
    "retention_period": 5,
    "active": true,
    "last_checked": "2025-01-15T10:00:00Z",
    "family_members": [ ... ],
    "close_associates": [ ... ],
    "created_at": "2024-06-01T12:00:00Z",
    "updated_at": "2025-01-15T10:00:00Z"
  }
}
```

### `POST /pep-persons`

Create a new PEP person.

**Roles:** User, Manager

**Request:**
```json
{
  "name": "Ухнаа Хүрэлсүх (Khurelsukh Ukhnaa)",
  "date_of_birth": "1968-06-14",
  "nationality_id": 143,
  "position": "head_state",
  "custom_position": null,
  "organization": "Government of Mongolia",
  "organization_type": "government",
  "status": "active",
  "start_date": 2021,
  "end_date": null,
  "source_of_wealth": "...",
  "source_of_funds": "...",
  "monitoring_frequency": "quarterly",
  "source": "...",
  "notes": "..."
}
```

**Validations applied:** Mongolian name format, unique (name + DOB), custom_position required if position='other', international PEP consistency.

**Response (201):** Created PEP Person object.

### `PUT /pep-persons/{id}`

Update a PEP person.

**Roles:** User, Manager

**Request:** Partial update (only fields to change).

**Response (200):** Updated PEP Person object.

### `DELETE /pep-persons/{id}`

Soft-delete (set active=false) or hard-delete.

**Roles:** Manager only

**Response (204):** No content.

### `POST /pep-persons/{id}/edd-xacxom`

Trigger EDD verification via xacxom web scraping for a specific PEP person.

**Roles:** User, Manager

**Response (200):**
```json
{
  "data": {
    "records_found": 5,
    "declarations": [
      {
        "name": "Ухнаа Хүрэлсүх",
        "position": "Ерөнхийлөгч",
        "organization": "Монгол Улс",
        "declaration_year": "2023",
        "aid_number": "12345"
      }
    ],
    "pep_updated": true
  }
}
```

**Errors:** 502 (scraping failed), 422 (name format cannot be parsed)

### `POST /pep-persons/{id}/request-approval`

Request senior management approval.

**Roles:** User, Manager

**Request:**
```json
{
  "approved_by_id": 2,
  "note": "Approved after reviewing financial declarations."
}
```

**Response (200):** Updated PEP Person object with approval fields set and edd_status='completed'.

### `POST /pep-persons/{id}/schedule-edd-review`

Mark the current date as the last EDD review date, triggering next_review recalculation.

**Response (200):** Updated PEP Person object.

---

## PEP Relationships

### `GET /pep-persons/{pep_id}/relationships`

List relationships for a specific PEP person.

**Query Parameters:**

| Param | Type | Description |
|-------|------|-------------|
| `relationship_type` | string | 'family' or 'associate' |
| `active` | bool | Filter by active (default: true) |

**Response (200):** List of Relationship objects.

### `GET /relationships/{id}`

Get a single relationship.

### `POST /pep-persons/{pep_id}/relationships`

Create a relationship for a PEP person.

**Roles:** User, Manager

**Request:**
```json
{
  "name": "Батсүх Гантулга",
  "relationship_type": "family",
  "family_relation": "spouse",
  "association_type": null,
  "date_of_birth": "1972-03-15",
  "nationality_id": 143,
  "edd_required": true,
  "source_of_wealth": "...",
  "source_of_funds": "...",
  "relationship_notes": "...",
  "verification_date": "2024-06-01",
  "verification_source": "Public records"
}
```

**Validations:** family_relation required if type='family', association_type required if type='associate'.

**Response (201):** Created Relationship object.

### `PUT /relationships/{id}`

Update a relationship.

**Roles:** User, Manager

### `DELETE /relationships/{id}`

**Roles:** Manager only

---

## PEP Screenings

### `GET /screenings`

List screenings. **Users see only their own; Managers see all.**

**Query Parameters:**

| Param | Type | Description |
|-------|------|-------------|
| `page` | int | Page number |
| `page_size` | int | Items per page |
| `result` | string | Filter by result (match/possible/no_match) |
| `screening_type` | string | Filter by screening_type |
| `screened_by` | int | Filter by user (Manager only) |
| `sort_by` | string | Default: screening_date |
| `sort_order` | string | Default: desc |

### `GET /screenings/{id}`

Get a single screening. **Users can only access their own.**

### `POST /screenings`

Create a new screening record.

**Roles:** User, Manager

**Request:**
```json
{
  "name": "John Doe",
  "date_of_birth": "1970-01-01",
  "nationality_id": 230,
  "screening_type": "initial",
  "trigger_reason": null,
  "screening_method": "database"
}
```

### `POST /screenings/{id}/run`

Execute the screening workflow (internal DB search → AI fallback).

**Response (200):**
```json
{
  "data": {
    "id": 42,
    "result": "match",
    "matched_pep_id": 7,
    "confidence_score": null,
    "screening_method": "database",
    "notes": "Internal DB Match: Found 'John Doe' (domestic, United States).",
    "screening_date": "2025-01-15T14:30:00Z"
  }
}
```

### `DELETE /screenings/{id}`

**Roles:** Manager only

---

## AI PEP Search

### `POST /ai/pep-search`

Search for PEP persons using AI.

**Roles:** User, Manager

**Request:**
```json
{
  "country_id": 143,
  "position": "Prime Minister",
  "year": "2020-2024",
  "ai_provider": "gemini",
  "ai_model": "gemini-2.5-flash"
}
```

**Response (200):**
```json
{
  "data": {
    "results": [
      {
        "name": "Ухнаа Хүрэлсүх (Khurelsukh Ukhnaa)",
        "specific_title": "Prime Minister of Mongolia",
        "start_year": 2017,
        "end_year": 2021,
        "birth_year": 1968,
        "notes": "Served as 30th PM; became President in 2021"
      }
    ]
  }
}
```

### `POST /ai/pep-search/create-person`

Create a PEP person from an AI search result line.

**Roles:** User, Manager

**Request:**
```json
{
  "name": "Ухнаа Хүрэлсүх (Khurelsukh Ukhnaa)",
  "specific_title": "Prime Minister of Mongolia",
  "start_year": 2017,
  "end_year": 2021,
  "birth_year": 1968,
  "notes": "...",
  "country_id": 143,
  "search_position": "Prime Minister",
  "search_year": "2020-2024"
}
```

**Validations:** Duplicate check on exact name + transliterated name (part in parentheses).

**Response (201):** Created PEP Person object.

---

## AI Position Search

### `POST /ai/position-search`

Search for PEP positions by country using AI.

**Roles:** User, Manager

**Request:**
```json
{
  "country_id": 143,
  "year": "2024",
  "ai_provider": "gemini",
  "ai_model": "gemini-2.5-flash"
}
```

**Response (200):**
```json
{
  "data": {
    "results": [
      {
        "position_title": "President of Mongolia",
        "category": "head_state",
        "notes": "Head of state, commander-in-chief of the armed forces"
      }
    ]
  }
}
```

### `POST /ai/position-search/register`

Register a position from AI results as a Position Template.

**Roles:** User, Manager

**Request:**
```json
{
  "position_title": "President of Mongolia",
  "category": "head_state",
  "country_id": 143,
  "year": "2024",
  "notes": "Head of state"
}
```

**Validations:** Duplicate check on (title, country, year).

**Response (201):** Created Position Template object.

---

## Position Templates

### `GET /position-templates`

List position templates with filtering.

**Query Parameters:**

| Param | Type | Description |
|-------|------|-------------|
| `country_id` | int | Filter by country |
| `category` | string | Filter by category |
| `year` | string | Filter by year |
| `active` | bool | Default: true |

### `GET /position-templates/{id}`

### `POST /position-templates`

**Roles:** User, Manager

### `PUT /position-templates/{id}`

**Roles:** Manager only

### `DELETE /position-templates/{id}`

**Roles:** Manager only

---

## Web Scraper

### `POST /scraper/start`

Start a background web scraping job.

**Roles:** User, Manager

**Request:**
```json
{
  "max_pages": 5
}
```

**Response (202):**
```json
{
  "data": {
    "job_id": "uuid-string",
    "status": "pending",
    "message": "Web scraping job has been queued."
  }
}
```

### `GET /scraper/jobs/{job_id}`

Check the status of a scraping job.

**Response (200):**
```json
{
  "data": {
    "job_id": "uuid-string",
    "status": "completed",
    "records_found": 47,
    "results": [
      {
        "name": "Ухнаа Хүрэлсүх",
        "position": "Ерөнхийлөгч",
        "organization": "Монгол Улс",
        "declaration_year": "2023",
        "aid_number": "12345"
      }
    ],
    "completed_at": "2025-01-15T14:35:00Z"
  }
}
```

---

## Countries

### `GET /countries`

List all countries (for dropdown selectors).

**Response (200):**
```json
{
  "data": [
    { "id": 143, "name": "Mongolia", "code": "MN" },
    { "id": 230, "name": "United States", "code": "US" }
  ]
}
```

---

## Audit Log

### `GET /audit-log`

**Roles:** Manager only

**Query Parameters:**

| Param | Type | Description |
|-------|------|-------------|
| `entity_type` | string | Filter by entity type |
| `entity_id` | int | Filter by specific record |
| `user_id` | int | Filter by who made the change |
| `from_date` | datetime | Start of date range |
| `to_date` | datetime | End of date range |
| `page` | int | |
| `page_size` | int | |

**Response (200):** Paginated list of audit log entries.

---

## Configuration

### `GET /config`

Get application configuration (AI models, company country, etc.).

**Roles:** Manager only

**Response (200):**
```json
{
  "data": {
    "company_country_id": 143,
    "gemini_model": "gemini-2.5-flash",
    "openai_model": "gpt-4o",
    "xacxom_search_url": "https://xacxom.iaac.mn/xacxom/search",
    "ai_providers_available": {
      "gemini": true,
      "openai": true
    }
  }
}
```

### `PUT /config`

Update application configuration.

**Roles:** Manager only
