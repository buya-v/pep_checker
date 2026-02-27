# Data Model — PEP Compliance Manager

## Entity Relationship Diagram (Text)

```
┌─────────────┐       ┌──────────────────┐       ┌─────────────┐
│   country    │       │    pep_person    │       │    user      │
│──────────────│       │──────────────────│       │─────────────│
│ id (PK)      │◄──┐   │ id (PK)          │   ┌──►│ id (PK)     │
│ name         │   │   │ name             │   │   │ email       │
│ code         │   │   │ name_phonetic    │   │   │ password    │
└──────────────┘   │   │ date_of_birth    │   │   │ full_name   │
                   ├───│ nationality_id   │   │   │ role        │
                   │   │ position         │   │   └─────────────┘
                   │   │ custom_position  │   │         ▲
                   │   │ organization     │   │         │
                   │   │ organization_type│   │         │
                   │   │ pep_type         │   │         │
                   │   │ status           │   │         │
                   │   │ start_date       │   │         │
                   │   │ end_date         │   │         │
                   │   │ risk_level       │   │         │
                   │   │ edd_status       │   │         │
                   │   │ edd_last_review  │   │         │
                   │   │ edd_next_review  │   │         │
                   │   │ monitoring_freq  │   │         │
                   │   │ senior_approval  │───┘         │
                   │   │ ...              │             │
                   │   └──────────────────┘             │
                   │        │ 1                         │
                   │        │                           │
                   │        │ *                         │
                   │   ┌──────────────────┐             │
                   │   │ pep_relationship │             │
                   │   │──────────────────│             │
                   │   │ id (PK)          │             │
                   │   │ pep_id (FK)      │             │
                   │   │ name             │             │
                   │   │ relationship_type│             │
                   ├───│ nationality_id   │             │
                   │   │ ...              │             │
                   │   └──────────────────┘             │
                   │                                    │
                   │   ┌──────────────────┐             │
                   │   │  pep_screening   │             │
                   │   │──────────────────│             │
                   │   │ id (PK)          │             │
                   │   │ name             │             │
                   ├───│ nationality_id   │             │
                   │   │ matched_pep_id   │─── pep_person
                   │   │ screened_by (FK) │─────────────┘
                   │   │ ...              │
                   │   └──────────────────┘
                   │
                   │   ┌─────────────────────┐
                   │   │ pep_position_template│
                   │   │─────────────────────│
                   │   │ id (PK)             │
                   │   │ name                │
                   │   │ category             │
                   ├───│ country_id (FK)     │
                   │   │ year                │
                   │   │ ...                 │
                   │   └─────────────────────┘
                   │
                   │   ┌──────────────────┐
                   │   │  audit_log        │
                   │   │──────────────────│
                   │   │ id (PK)          │
                   │   │ entity_type      │
                   │   │ entity_id        │
                   │   │ user_id (FK)     │── user
                   │   │ field_name       │
                   │   │ old_value        │
                   │   │ new_value        │
                   │   │ timestamp        │
                   │   └──────────────────┘
```

---

## Table Definitions

### 1. `user`

| Column | Type | Nullable | Default | Constraints |
|--------|------|----------|---------|-------------|
| `id` | SERIAL / UUID | No | auto | PRIMARY KEY |
| `email` | VARCHAR(255) | No | — | UNIQUE, NOT NULL |
| `password_hash` | VARCHAR(255) | No | — | NOT NULL |
| `full_name` | VARCHAR(255) | No | — | NOT NULL |
| `role` | VARCHAR(20) | No | 'user' | CHECK(role IN ('user', 'manager')) |
| `is_active` | BOOLEAN | No | true | |
| `created_at` | TIMESTAMPTZ | No | now() | |
| `updated_at` | TIMESTAMPTZ | No | now() | |

**Indexes:**
- `idx_user_email` on `email` (unique)

---

### 2. `country`

| Column | Type | Nullable | Default | Constraints |
|--------|------|----------|---------|-------------|
| `id` | SERIAL | No | auto | PRIMARY KEY |
| `name` | VARCHAR(100) | No | — | NOT NULL |
| `code` | CHAR(2) | No | — | UNIQUE, NOT NULL |

**Indexes:**
- `idx_country_code` on `code` (unique)

**Seed data**: All ISO 3166-1 alpha-2 countries. Especially important: Mongolia (`MN`).

---

### 3. `pep_person`

| Column | Type | Nullable | Default | Constraints |
|--------|------|----------|---------|-------------|
| `id` | SERIAL / UUID | No | auto | PRIMARY KEY |
| `name` | VARCHAR(255) | No | — | NOT NULL |
| `name_phonetic` | VARCHAR(255) | Yes | — | Computed, stored |
| `date_of_birth` | DATE | Yes | — | |
| `nationality_id` | INTEGER | Yes | — | FK → country(id) |
| `position` | VARCHAR(30) | No | — | NOT NULL, CHECK(position IN (...)) |
| `custom_position` | VARCHAR(255) | Yes | — | |
| `organization` | VARCHAR(255) | No | — | NOT NULL |
| `organization_type` | VARCHAR(30) | Yes | — | CHECK(organization_type IN (...)) |
| `pep_type` | VARCHAR(20) | Yes | — | Computed, stored. CHECK(pep_type IN ('domestic','foreign','international')) |
| `status` | VARCHAR(20) | No | 'active' | CHECK(status IN ('active','former','deceased')) |
| `start_date` | INTEGER | Yes | — | Year (e.g. 2020) |
| `end_date` | INTEGER | Yes | — | Year (e.g. 2024) |
| `risk_level` | VARCHAR(10) | Yes | — | Computed, stored. CHECK(risk_level IN ('low','medium','high')) |
| `edd_status` | VARCHAR(20) | No | 'pending' | CHECK(edd_status IN ('pending','in_progress','completed','review_needed')) |
| `edd_last_review` | DATE | Yes | — | |
| `edd_next_review` | DATE | Yes | — | Computed, stored |
| `monitoring_frequency` | VARCHAR(20) | No | 'quarterly' | CHECK(monitoring_frequency IN ('monthly','quarterly','semi_annual','annual')) |
| `senior_approval_id` | INTEGER | Yes | — | FK → user(id) |
| `senior_approval_date` | TIMESTAMPTZ | Yes | — | |
| `source_of_wealth` | TEXT | Yes | — | |
| `source_of_funds` | TEXT | Yes | — | |
| `source` | TEXT | Yes | — | |
| `source_url` | VARCHAR(500) | Yes | — | |
| `source_date` | DATE | Yes | — | |
| `notes` | TEXT | Yes | — | |
| `self_declared` | BOOLEAN | No | false | |
| `self_declaration_date` | DATE | Yes | — | |
| `retention_period` | INTEGER | No | 5 | |
| `active` | BOOLEAN | No | true | |
| `last_checked` | TIMESTAMPTZ | Yes | now() | |
| `created_at` | TIMESTAMPTZ | No | now() | |
| `updated_at` | TIMESTAMPTZ | No | now() | |
| `created_by` | INTEGER | Yes | — | FK → user(id) |

**Constraints:**
- `uq_pep_person_name_dob` UNIQUE(`name`, `date_of_birth`) — prevents duplicate PEP entries

**Indexes:**
- `idx_pep_person_name_phonetic` on `name_phonetic`
- `idx_pep_person_nationality` on `nationality_id`
- `idx_pep_person_position` on `position`
- `idx_pep_person_organization` on `organization`
- `idx_pep_person_start_date` on `start_date`
- `idx_pep_person_end_date` on `end_date`
- `idx_pep_person_last_checked` on `last_checked`
- `idx_pep_person_source_url` on `source_url`
- `idx_pep_person_source_date` on `source_date`
- GIN index on `name` using `pg_trgm` for fuzzy text search (optional enhancement)

---

### 4. `pep_relationship`

| Column | Type | Nullable | Default | Constraints |
|--------|------|----------|---------|-------------|
| `id` | SERIAL / UUID | No | auto | PRIMARY KEY |
| `pep_id` | INTEGER | No | — | FK → pep_person(id) ON DELETE CASCADE |
| `name` | VARCHAR(255) | No | — | NOT NULL |
| `relationship_type` | VARCHAR(20) | No | — | NOT NULL, CHECK(relationship_type IN ('family','associate')) |
| `family_relation` | VARCHAR(20) | Yes | — | CHECK(family_relation IN ('spouse','child','child_spouse','parent','sibling','other')) |
| `association_type` | VARCHAR(30) | Yes | — | CHECK(association_type IN ('business_partner','joint_owner','legal_arrangement','close_business','other')) |
| `date_of_birth` | DATE | Yes | — | |
| `nationality_id` | INTEGER | Yes | — | FK → country(id) |
| `edd_required` | BOOLEAN | No | true | |
| `source_of_wealth` | TEXT | Yes | — | |
| `source_of_funds` | TEXT | Yes | — | |
| `relationship_notes` | TEXT | Yes | — | |
| `verification_date` | DATE | Yes | — | |
| `verification_source` | TEXT | Yes | — | |
| `active` | BOOLEAN | No | true | |
| `created_at` | TIMESTAMPTZ | No | now() | |
| `updated_at` | TIMESTAMPTZ | No | now() | |

**Indexes:**
- `idx_pep_relationship_pep_id` on `pep_id`

**Application-level check constraints:**
- If `relationship_type = 'family'` then `family_relation` must not be NULL
- If `relationship_type = 'associate'` then `association_type` must not be NULL

---

### 5. `pep_screening`

| Column | Type | Nullable | Default | Constraints |
|--------|------|----------|---------|-------------|
| `id` | SERIAL / UUID | No | auto | PRIMARY KEY |
| `name` | VARCHAR(255) | No | — | NOT NULL |
| `date_of_birth` | DATE | Yes | — | |
| `nationality_id` | INTEGER | Yes | — | FK → country(id) |
| `screening_date` | TIMESTAMPTZ | No | now() | NOT NULL |
| `screening_type` | VARCHAR(20) | No | 'initial' | NOT NULL, CHECK(screening_type IN ('initial','periodic','trigger','exit')) |
| `trigger_reason` | VARCHAR(20) | Yes | — | CHECK(trigger_reason IN ('news','transaction','structure','other')) |
| `result` | VARCHAR(20) | Yes | — | CHECK(result IN ('match','possible','no_match')) |
| `matched_pep_id` | INTEGER | Yes | — | FK → pep_person(id) ON DELETE SET NULL |
| `confidence_score` | FLOAT | Yes | — | |
| `screened_by` | INTEGER | No | — | FK → user(id), NOT NULL |
| `screening_method` | VARCHAR(20) | No | — | NOT NULL, CHECK(screening_method IN ('database','media','official','manual','ai_screening')) |
| `database_used` | VARCHAR(20) | Yes | — | CHECK(database_used IN ('worldcheck','dowjones','refinitiv','other')) |
| `evidence_refs` | TEXT | Yes | — | |
| `notes` | TEXT | Yes | — | |
| `created_at` | TIMESTAMPTZ | No | now() | |
| `updated_at` | TIMESTAMPTZ | No | now() | |

**Indexes:**
- `idx_pep_screening_date` on `screening_date` (DESC)
- `idx_pep_screening_nationality` on `nationality_id`
- `idx_pep_screening_matched_pep` on `matched_pep_id`
- `idx_pep_screening_screened_by` on `screened_by`

**Default ordering:** `screening_date DESC`

---

### 6. `pep_position_template`

| Column | Type | Nullable | Default | Constraints |
|--------|------|----------|---------|-------------|
| `id` | SERIAL / UUID | No | auto | PRIMARY KEY |
| `name` | VARCHAR(255) | No | — | NOT NULL |
| `category` | VARCHAR(30) | No | — | NOT NULL, CHECK(category IN (...position enum values...)) |
| `country_id` | INTEGER | Yes | — | FK → country(id) |
| `year` | VARCHAR(20) | Yes | — | |
| `notes` | TEXT | Yes | — | |
| `active` | BOOLEAN | No | true | |
| `created_at` | TIMESTAMPTZ | No | now() | |
| `updated_at` | TIMESTAMPTZ | No | now() | |

**Constraints:**
- `uq_position_template_name_country_year` UNIQUE(`name`, `country_id`, `year`)

**Indexes:**
- `idx_position_template_name` on `name`
- `idx_position_template_category` on `category`
- `idx_position_template_country` on `country_id`

**Default ordering:** `country_id, name`

---

### 7. `audit_log`

| Column | Type | Nullable | Default | Constraints |
|--------|------|----------|---------|-------------|
| `id` | BIGSERIAL | No | auto | PRIMARY KEY |
| `entity_type` | VARCHAR(50) | No | — | NOT NULL (e.g., 'pep_person', 'pep_screening') |
| `entity_id` | INTEGER | No | — | NOT NULL |
| `user_id` | INTEGER | Yes | — | FK → user(id) ON DELETE SET NULL |
| `action` | VARCHAR(20) | No | — | NOT NULL, CHECK(action IN ('create','update','delete')) |
| `field_name` | VARCHAR(100) | Yes | — | NULL for create/delete actions |
| `old_value` | TEXT | Yes | — | |
| `new_value` | TEXT | Yes | — | |
| `timestamp` | TIMESTAMPTZ | No | now() | NOT NULL |

**Indexes:**
- `idx_audit_log_entity` on `(entity_type, entity_id)`
- `idx_audit_log_timestamp` on `timestamp` (DESC)
- `idx_audit_log_user` on `user_id`

**Notes:**
- This table is append-only. No updates or deletes.
- Partition by month if expected volume is high.

---

### 8. `background_job` (optional — if not using Celery's built-in result backend)

| Column | Type | Nullable | Default | Constraints |
|--------|------|----------|---------|-------------|
| `id` | UUID | No | auto | PRIMARY KEY |
| `job_type` | VARCHAR(50) | No | — | e.g., 'web_scraping', 'edd_review' |
| `status` | VARCHAR(20) | No | 'pending' | CHECK(status IN ('pending','running','completed','failed')) |
| `created_by` | INTEGER | No | — | FK → user(id) |
| `params` | JSONB | Yes | — | Job parameters |
| `result` | JSONB | Yes | — | Job result data |
| `error_message` | TEXT | Yes | — | |
| `created_at` | TIMESTAMPTZ | No | now() | |
| `completed_at` | TIMESTAMPTZ | Yes | — | |

---

## Recommended PostgreSQL Extensions

```sql
CREATE EXTENSION IF NOT EXISTS pg_trgm;  -- Fuzzy text search
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";  -- UUID generation (if using UUID PKs)
```

## Migration Strategy

Use **Alembic** (for SQLAlchemy) or an equivalent migration tool. Keep migrations in `backend/migrations/`.

### Initial Migration Checklist

1. Create `country` table + seed all ISO countries
2. Create `user` table + seed admin user
3. Create `pep_person` table with all constraints and indexes
4. Create `pep_relationship` table
5. Create `pep_screening` table
6. Create `pep_position_template` table
7. Create `audit_log` table
8. Create `background_job` table (optional)
