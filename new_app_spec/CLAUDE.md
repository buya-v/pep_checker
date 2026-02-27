# CLAUDE.md - PEP Compliance Manager

## Project Overview

PEP Compliance Manager is a **standalone web application** for managing Politically Exposed Persons (PEPs) as part of AML/KYC compliance. It replaces an existing Odoo module with a modern, framework-independent architecture.

**Core capabilities:**
- PEP database management (persons, relationships, positions)
- AI-powered PEP screening via Google Gemini and OpenAI
- Web scraping from official Mongolian government sources (xacxom.iaac.mn)
- Enhanced Due Diligence (EDD) workflows with approval chains
- Fuzzy/phonetic name matching for screening
- Role-based access control (User vs Manager)
- Audit trail and activity logging

## Tech Stack (Recommended)

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| **Backend** | Python (FastAPI or Flask) | Matches team expertise from Odoo; async support for AI calls |
| **Database** | PostgreSQL | Relational integrity for PEP data; full-text + trigram search |
| **ORM** | SQLAlchemy 2.0 | Mature Python ORM with migration support (Alembic) |
| **Frontend** | React or Vue.js + TypeScript | Component-based UI with good table/form support |
| **Task Queue** | Celery + Redis | Background scraping jobs, scheduled EDD reviews |
| **Auth** | JWT tokens + bcrypt | Stateless auth with role-based access |
| **AI** | google-generativeai, openai SDKs | Dual-provider AI integration |
| **Search** | jellyfish (phonetic), pg_trgm | Fuzzy name matching |

## Specification Files

Read these files **in order** before starting development:

1. **`SPEC.md`** — Complete feature specification with all business rules, workflows, validation constraints, and user stories
2. **`DATA_MODEL.md`** — Database schema with all tables, columns, types, constraints, relationships, and indexes
3. **`API_SPEC.md`** — REST API endpoints with request/response schemas, authentication, and error handling
4. **`UI_SPEC.md`** — Page layouts, component hierarchy, forms, tables, search/filter behavior, and navigation

## Architecture Principles

- **Separation of concerns**: API layer, service/business logic layer, data access layer
- **AI provider abstraction**: A single interface that works with both Gemini and OpenAI; easy to add new providers
- **Graceful degradation**: AI and scraping features should fail with clear user messages if API keys are missing or services are unavailable
- **Background processing**: Web scraping and bulk operations run as async background tasks with user notifications on completion
- **Audit trail**: All PEP record changes must be logged with timestamp, user, and before/after values

## Key Business Rules (Summary)

These are detailed fully in `SPEC.md`. Critical rules to always enforce:

1. **Unique constraint**: No two PEP persons can share the same (name + date_of_birth)
2. **Mongolian name format**: Mongolian PEPs must use format `Cyrillic Name (Latin Name)` — regex: `^[\u0400-\u04FF\s.\-]+\s\([\w\s.\-]+\)$`
3. **Risk level auto-calculation**: Based on pep_type, position, status, and years since leaving office
4. **PEP type derivation**: Computed from nationality vs. company country and organization type
5. **EDD next-review date**: Computed from last review + monitoring frequency
6. **Screening workflow**: Always check internal DB first (phonetic + text match), then fall back to AI
7. **Relationship validation**: Family members require `family_relation`; associates require `association_type`
8. **International PEP consistency**: International PEPs must have organization_type = 'international_org'

## Development Workflow

```bash
# Backend
cd backend/
pip install -r requirements.txt
alembic upgrade head          # Run migrations
pytest                         # Run tests
uvicorn app.main:app --reload  # Start dev server

# Frontend
cd frontend/
npm install
npm run dev                    # Start dev server
npm run test                   # Run tests
npm run build                  # Production build
```

## Environment Variables

```env
# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/pep_compliance

# AI Providers
GOOGLE_API_KEY=<your-gemini-key>
OPENAI_API_KEY=<your-openai-key>
GEMINI_MODEL=gemini-2.5-flash
OPENAI_MODEL=gpt-4o

# Web Scraping
XACXOM_SEARCH_URL=https://xacxom.iaac.mn/xacxom/search

# Auth
JWT_SECRET=<random-secret>
JWT_EXPIRY_HOURS=24

# Background Tasks
CELERY_BROKER_URL=redis://localhost:6379/0
```

## Coding Conventions

- **Python**: snake_case for functions/variables, PascalCase for classes, UPPER_CASE for constants
- **TypeScript**: camelCase for functions/variables, PascalCase for components/types
- **API routes**: kebab-case (e.g., `/api/pep-persons`, `/api/screenings`)
- **Database tables**: snake_case (e.g., `pep_person`, `pep_screening`)
- **Test files**: `test_<module>.py` (backend), `<Component>.test.tsx` (frontend)
- **Error handling**: Use structured error responses with error codes
- **Logging**: Use Python `logging` module; log all AI calls, scraping operations, and auth events

## Security Requirements

- Two roles: **User** (read, write, create) and **Manager** (full CRUD including delete)
- Users can only see their own screening records; managers see all
- API keys stored as environment variables, never in code or database
- All user inputs sanitized; parameterized queries only
- Rate limiting on AI and scraping endpoints
- CORS configured for frontend origin only

## Important Notes

- **Mongolia-specific**: The app has special handling for Mongolian Cyrillic names and scrapes the Mongolian government source xacxom.iaac.mn. Handle Unicode properly throughout.
- **Dual AI providers**: Both Gemini and OpenAI must be supported. The user picks which to use per operation.
- **Prompt templates**: AI prompts should be stored as configurable templates, not hard-coded strings. See `SPEC.md` for exact prompt text.
- **No Odoo dependency**: This is a standalone app. Do not use any Odoo libraries, patterns, or conventions.
