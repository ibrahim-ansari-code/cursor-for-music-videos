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
poetry run alembic revision -m "migration_message"
poetry run alembic upgrade head
poetry run alembic downgrade -1

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
- Use Alembic for all schema changes

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
- `Frontend/src/utils/api/` - Backend API integration layer
- `Frontend/src/contexts/` - React contexts (primarily auth)

### Key Files
- `Backend/database.py` - Database connection and session management
- `Backend/config.py` - Application configuration
- `Frontend/src/components/ui/SharedModalComponents.jsx` - Shared receipt upload pattern
- `Frontend/ARCHITECTURE.md` - Frontend architectural documentation
- `Backend/tests/backend_test_suite_guide.md` - Testing documentation

## Deployment

- **Branching**: `feature/*` → `dev` → `main`
- **Platform**: Porter for both frontend and backend
- **Environments**: Production (`main` branch) + preview environments (PRs)
- **Build**: Docker containers with Poetry for backend, npm for frontend