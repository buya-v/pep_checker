# PEP Compliance Manager — New App Specification

This directory contains all specification files needed to build a **standalone PEP Compliance Manager** web application from scratch. These files are designed to be used with Claude (or any AI assistant) to generate the full application.

## What's Inside

| File | Purpose |
|------|---------|
| `CLAUDE.md` | Project overview, tech stack, conventions, and instructions for AI assistants |
| `SPEC.md` | Complete feature specification — all business rules, workflows, validations, enums, computed fields, AI prompts, and data processing logic |
| `DATA_MODEL.md` | Database schema — all tables, columns, types, constraints, indexes, and relationships |
| `API_SPEC.md` | REST API specification — all endpoints, request/response schemas, auth, errors |
| `UI_SPEC.md` | UI layout specification — page wireframes, navigation, components, conditional visibility, responsive behavior |
| `PROJECT_STRUCTURE.md` | Recommended directory structure for backend (FastAPI) and frontend (React) |
| `.env.example` | Environment variable template |
| `docker-compose.yml` | Local development services (PostgreSQL + Redis) |
| `backend-requirements.txt` | Python package dependencies |
| `frontend-package.json` | Node.js package dependencies |

## How to Use

### Starting a New Project

1. Create a new repository for the app
2. Copy `CLAUDE.md` to the repo root
3. Copy `SPEC.md`, `DATA_MODEL.md`, `API_SPEC.md`, `UI_SPEC.md` into a `docs/` directory
4. Copy `.env.example`, `docker-compose.yml` to the repo root
5. Use `PROJECT_STRUCTURE.md` to scaffold the directory layout
6. Use `backend-requirements.txt` and `frontend-package.json` as starting dependency files

### Working with Claude

Tell Claude:

> "Read the CLAUDE.md and all spec files in the docs/ directory, then implement the application following the specifications exactly."

Claude will have all the context needed to:
- Set up the database models and migrations
- Build the API layer with proper auth and validation
- Implement the AI provider integration
- Build the web scraping service
- Create the screening workflow
- Build the frontend pages and components

## Features Covered

- PEP person database (CRUD, computed fields, validations)
- Family member and close associate relationships
- Name screening with phonetic matching + AI fallback
- AI-powered PEP discovery (Gemini + OpenAI)
- AI-powered position discovery by country
- Web scraping from Mongolian government sources
- Enhanced Due Diligence workflows with approval chains
- Role-based access control (User vs Manager)
- Audit trail for all record changes
- Background job processing for scraping
- Scheduled EDD review notifications
