# Recommended Project Structure

```
pep-compliance-manager/
├── CLAUDE.md                         # Copy from new_app_spec/CLAUDE.md
├── docker-compose.yml                # PostgreSQL + Redis for local dev
├── .env.example                      # Template for environment variables
│
├── backend/
│   ├── requirements.txt              # Python dependencies
│   ├── alembic.ini                   # Alembic migration config
│   ├── migrations/                   # Database migrations (auto-generated)
│   │   └── versions/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                   # FastAPI app entry point
│   │   ├── config.py                 # Settings from env vars
│   │   ├── database.py               # SQLAlchemy engine + session
│   │   │
│   │   ├── models/                   # SQLAlchemy ORM models
│   │   │   ├── __init__.py
│   │   │   ├── user.py               # User model
│   │   │   ├── country.py            # Country reference model
│   │   │   ├── pep_person.py         # PEP Person model
│   │   │   ├── pep_relationship.py   # Relationship model
│   │   │   ├── pep_screening.py      # Screening model
│   │   │   ├── position_template.py  # Position Template model
│   │   │   └── audit_log.py          # Audit log model
│   │   │
│   │   ├── schemas/                  # Pydantic request/response schemas
│   │   │   ├── __init__.py
│   │   │   ├── auth.py
│   │   │   ├── pep_person.py
│   │   │   ├── pep_relationship.py
│   │   │   ├── pep_screening.py
│   │   │   ├── position_template.py
│   │   │   ├── ai_search.py
│   │   │   └── common.py             # Pagination, error responses
│   │   │
│   │   ├── api/                      # Route handlers
│   │   │   ├── __init__.py
│   │   │   ├── auth.py               # /auth/*
│   │   │   ├── pep_persons.py        # /pep-persons/*
│   │   │   ├── relationships.py      # /relationships/*
│   │   │   ├── screenings.py         # /screenings/*
│   │   │   ├── ai_search.py          # /ai/*
│   │   │   ├── position_templates.py # /position-templates/*
│   │   │   ├── scraper.py            # /scraper/*
│   │   │   ├── audit_log.py          # /audit-log
│   │   │   └── config.py             # /config
│   │   │
│   │   ├── services/                 # Business logic layer
│   │   │   ├── __init__.py
│   │   │   ├── pep_person_service.py # PEP CRUD + computed fields
│   │   │   ├── screening_service.py  # Screening workflow (DB search → AI)
│   │   │   ├── ai_service.py         # AI provider abstraction
│   │   │   ├── scraper_service.py    # xacxom web scraping
│   │   │   ├── phonetic_service.py   # Jellyfish phonetic matching
│   │   │   └── audit_service.py      # Audit logging
│   │   │
│   │   ├── core/                     # Cross-cutting concerns
│   │   │   ├── __init__.py
│   │   │   ├── auth.py               # JWT creation/validation
│   │   │   ├── dependencies.py       # FastAPI dependencies (get_db, get_current_user)
│   │   │   ├── permissions.py        # Role-based access decorators
│   │   │   └── exceptions.py         # Custom exception classes
│   │   │
│   │   └── tasks/                    # Celery background tasks
│   │       ├── __init__.py
│   │       ├── celery_app.py         # Celery configuration
│   │       ├── scraping_tasks.py     # Background scraping
│   │       └── edd_review_tasks.py   # Scheduled EDD review checker
│   │
│   └── tests/
│       ├── __init__.py
│       ├── conftest.py               # Fixtures (test DB, test client, test users)
│       ├── test_pep_person.py
│       ├── test_screening.py
│       ├── test_relationships.py
│       ├── test_ai_service.py
│       ├── test_scraper_service.py
│       └── test_auth.py
│
├── frontend/
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts                # Or next.config.js
│   ├── src/
│   │   ├── main.tsx                  # App entry point
│   │   ├── App.tsx                   # Root component + routing
│   │   │
│   │   ├── api/                      # API client layer
│   │   │   ├── client.ts             # Axios/fetch wrapper with auth
│   │   │   ├── pepPersons.ts
│   │   │   ├── screenings.ts
│   │   │   ├── aiSearch.ts
│   │   │   ├── scraper.ts
│   │   │   └── auth.ts
│   │   │
│   │   ├── pages/                    # Route-level page components
│   │   │   ├── PepPersonList.tsx
│   │   │   ├── PepPersonDetail.tsx
│   │   │   ├── PepPersonForm.tsx
│   │   │   ├── ScreeningList.tsx
│   │   │   ├── ScreeningDetail.tsx
│   │   │   ├── AiPepSearch.tsx
│   │   │   ├── AiPositionSearch.tsx
│   │   │   ├── WebScraper.tsx
│   │   │   ├── PositionTemplates.tsx
│   │   │   ├── Settings.tsx
│   │   │   └── Login.tsx
│   │   │
│   │   ├── components/               # Shared UI components
│   │   │   ├── Layout.tsx            # Nav + sidebar + content area
│   │   │   ├── DataTable.tsx         # Sortable, paginated table
│   │   │   ├── StatusBadge.tsx       # Color-coded badge/chip
│   │   │   ├── StatusBar.tsx         # EDD workflow progress
│   │   │   ├── SearchFilters.tsx     # Search + dropdown filters
│   │   │   ├── ConfirmDialog.tsx     # Confirmation modal
│   │   │   ├── ApprovalModal.tsx     # Senior approval dialog
│   │   │   ├── EmptyState.tsx        # No-data illustration
│   │   │   └── Toast.tsx             # Notification toasts
│   │   │
│   │   ├── hooks/                    # Custom React hooks
│   │   │   ├── useAuth.ts
│   │   │   ├── usePagination.ts
│   │   │   └── useToast.ts
│   │   │
│   │   ├── context/                  # React context providers
│   │   │   └── AuthContext.tsx
│   │   │
│   │   ├── types/                    # TypeScript type definitions
│   │   │   ├── pepPerson.ts
│   │   │   ├── screening.ts
│   │   │   ├── relationship.ts
│   │   │   ├── positionTemplate.ts
│   │   │   └── common.ts
│   │   │
│   │   └── utils/                    # Helper utilities
│   │       ├── formatters.ts         # Date, enum label formatters
│   │       └── validators.ts         # Client-side validation
│   │
│   └── tests/
│       └── ...
│
└── docs/                             # Specification documents
    ├── SPEC.md
    ├── DATA_MODEL.md
    ├── API_SPEC.md
    └── UI_SPEC.md
```
