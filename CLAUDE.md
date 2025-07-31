# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Backend Development

```bash
# Install dependencies
poetry install

# Run backend server
poetry run uvicorn Backend.api.app:app --reload

# Database migrations
poetry run alembic revision --autogenerate -m "migration_message"
poetry run alembic upgrade head
poetry run alembic downgrade -1

# Supabase migrations (for schema changes)
supabase db diff --use-migra -f migration_name
supabase db push

# Run tests
cd Backend/tests
python run_all_api_tests_pytest.py
python -m pytest api_tests/ -v
python -m pytest integration_tests/ -v
python -m pytest unit_tests/ -v
```

### Frontend Development

```bash
cd Frontend
npm install
npm run dev
npm run build
```

### Prerequisites for Testing

- Backend server must be running at `http://localhost:8000`
- Valid `.test_credentials.json` file in `Backend/tests/` directory
- Environment variables configured in `.env` files

## Architecture Overview

### Backend Architecture

- **Tech Stack**: FastAPI + SQLModel + PostgreSQL + Alembic
- **Auth**: Supabase JWT with user sync
- **Database**: Async PostgreSQL with SQLAlchemy
- **API Pattern**: Domain-based routers (`/api/accounting`, `/api/properties`, etc.)
- **Structure**: Each domain has `router.py`, `schemas.py`, `service.py`, `helpers.py`

### Frontend Architecture

- **Tech Stack**: React 18 + Vite + Tailwind CSS + React Router v7
- **State**: Context for auth, local state for components
- **API**: Domain-separated modules in `src/utils/api/`
- **Patterns**: Shared receipt upload system, modal patterns, controlled forms

### Key Integrations

- **Supabase**: Authentication and user management
- **QuickBooks**: Accounting integration via Apideck
- **Azure Blob Storage**: File storage for receipts and documents
- **OpenAI**: AI-powered receipt parsing

## Development Patterns

### Backend Patterns

- Use async/await for all database operations
- Follow domain-driven design with modular API routers
- Implement circuit breakers for external service calls
- Use Pydantic schemas for request/response validation
- Maintain comprehensive test coverage (unit, integration, API tests)

### Frontend Patterns

- Use the shared receipt upload pattern for file handling (see `Frontend/ARCHITECTURE.md`)
- Implement functional setState to avoid stale closures
- Follow the modal pattern with shared components from `ui/SharedModalComponents.jsx`
- Use domain-specific API modules for backend communication
- Handle loading states and error boundaries consistently

### Database Patterns

- Use UUID primary keys across all models
- Implement proper cascade deletes for parent-child relationships
- Add `created_at`/`updated_at` timestamps to all entities

### Migration Strategy

#### IMPORTANT: Dual migration system - Supabase + Alembic working together

#### Current Setup

- **Production Database**: Managed via Alembic migrations (`Backend/migrations/versions/`)
- **Local Development**: Synced via Supabase migrations (`supabase/migrations/`)
- **Baseline**: `supabase/migrations/20250622235642_baseline_sync_from_remote.sql` contains full production schema

#### Migration Types & When to Use

1. **Alembic Migrations (Primary for Production)**

   - **Use for**: Changes to SQLModel classes in `Backend/models/`
   - **Generate**: `poetry run alembic revision --autogenerate -m "description"`
   - **Apply locally**: `poetry run alembic upgrade head`
   - **Deploy**: Automatic via production deployment

   ##### Alembic Use Cases

   - Adding/removing model classes (e.g., `class Vendor(SQLModel, table=True)`)
   - Adding/removing fields to models (e.g., `email: str | None = None`)
   - Changing field types or constraints (e.g., `Field(max_length=255)`)
   - Adding/removing indexes defined in SQLModel
   - Modifying foreign key relationships

2. **Supabase Migrations (Local Development + DB-specific features)**
   - **Use for**: Database features not representable in SQLModel
   - **Generate**: `supabase db diff --use-migra -f migration_name`
   - **Apply locally**: `supabase db push`
   - **Deploy**: Manual coordination with Alembic

   ##### Supabase Use Cases

   - Row Level Security (RLS) policies
   - Database functions and triggers
   - Custom SQL types or enums beyond SQLModel support
   - Database views or materialized views
   - Specialized indexes (GIN for text search, GiST for spatial data)
   - Data migration scripts or bulk updates

#### Recommended Workflows

#### Scenario A: SQLModel Changes (Most Common)

```bash
# 1. Modify SQLModel classes in Backend/models/
# 2. Generate Alembic migration
cd Backend
poetry run alembic revision --autogenerate -m "add new feature table"

# 3. Apply locally
poetry run alembic upgrade head

# 4. Commit and deploy - Alembic runs automatically in production
git add Backend/migrations/versions/
git commit -m "feat: add new feature table"
```

#### Scenario B: Database-Specific Changes

```bash
# 1. Make changes via Supabase Studio or direct SQL
# 2. Generate Supabase migration
supabase db diff --use-migra -f add_rls_policies

# 3. Apply locally
supabase db push

# 4. Manually apply to production (coordinate with DevOps)
# 5. Create matching Alembic migration if needed for model sync
```

#### Team Onboarding

- New developers run `supabase start` → Automatically gets exact production schema
- Local database matches remote via baseline migration
- No manual schema setup required

#### Migration Files

- `Backend/migrations/versions/` - Alembic migrations (production)
- `supabase/migrations/` - Supabase migrations (local dev + supplemental)
- Both directories should be committed to Git

### Testing Requirements

- Backend API server must be running for tests
- Use session-scoped authentication tokens for efficiency
- Run tests from `Backend/tests` directory
- Configure test credentials in `.test_credentials.json`

## File Structure Highlights

### Critical Directories

- `Backend/api/` - FastAPI routers organized by domain
- `Backend/models/` - SQLModel database models
- `Backend/tests/` - Comprehensive test suite
- `Frontend/src/components/ui/` - Shared UI components
- `Frontend/src/components/charts/` - Chart components using Recharts
- `Frontend/src/utils/api/` - Backend API integration layer
- `Frontend/src/contexts/` - React contexts (primarily auth)

### Key Files

- `Backend/database.py` - Database connection and session management
- `Backend/config.py` - Application configuration
- `Frontend/src/components/ui/SharedModalComponents.jsx` - Shared receipt upload pattern
- `Frontend/src/components/charts/CHARTS.md` - Chart components documentation
- `Frontend/ARCHITECTURE.md` - Frontend architectural documentation
- `Backend/tests/Backend-Test-Suite-Guide.md` - Comprehensive testing documentation

## Deployment

- **Branching**: `feature/*` → `dev` → `main`
- **Platform**: Porter for both frontend and backend
- **Environments**: Production (`main` branch) + preview environments (PRs)
- **Build**: Docker containers with Poetry for backend, npm for frontend
