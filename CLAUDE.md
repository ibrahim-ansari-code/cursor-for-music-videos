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

# Run tests (ALWAYS use poetry)
cd Backend/tests
poetry run pytest unit_tests/ -v
poetry run pytest api_tests/ -v
poetry run pytest integration_tests/ -v
# Or run all tests
python run_all_api_tests_pytest.py
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
- **Monitoring**: Sentry for error tracking, performance monitoring, and logging

### Key Integrations

- **Supabase**: Authentication and user management
- **QuickBooks**: Accounting integration via Apideck
- **Azure Blob Storage**: File storage for receipts and documents
- **OpenAI**: AI-powered receipt parsing
- **Sentry**: Error tracking, performance monitoring, and structured logging

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
- Handle loading states and error boundaries consistently with Sentry integration
- All error boundaries should report to Sentry with contextual tags and business context

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

```text

#### Database-Specific Changes

```bash
# 1. Make changes via Supabase Studio or direct SQL
# 2. Generate Supabase migration
supabase db diff --use-migra -f add_rls_policies

# 3. Apply locally
supabase db reset

# 4. PR will automatically apply to production when closed
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

- **ALWAYS use Poetry to run backend tests**: `poetry run pytest` not `python -m pytest`
- Backend API server must be running for API tests
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

## Sentry Integration Patterns

### Error / Exception Tracking

- Use `Sentry.captureException(error)` to capture exceptions in try-catch blocks
- All error boundaries must import and use `import * as Sentry from "@sentry/react"`
- Include contextual tags for better error categorization and business context

#### Error Boundary Integration Example

```javascript
import * as Sentry from '@sentry/react';

componentDidCatch(error, errorInfo) {
  Sentry.captureException(error, {
    tags: {
      component: 'FinancialErrorBoundary',
      action: 'invoice_generation',
      financial: true,
    },
    contexts: {
      react: {
        componentStack: errorInfo.componentStack,
      },
      business: {
        feature: 'accounting',
        userType: 'landlord',
      }
    }
  });
}
```

### Performance Tracing

Create custom spans for meaningful user actions and API calls using `Sentry.startSpan`:

#### UI Component Tracing

```javascript
const handlePropertyCreation = () => {
  Sentry.startSpan(
    {
      op: "ui.click",
      name: "Property Creation Flow",
    },
    (span) => {
      span.setAttribute("propertyType", "apartment");
      span.setAttribute("stepNumber", currentStep);
      span.setAttribute("unitsCount", formData.totalUnits);
      
      // Perform property creation
      createProperty();
    },
  );
};
```

#### API Call Tracing  

```javascript
async function fetchAccountingData(propertyId) {
  return Sentry.startSpan(
    {
      op: "http.client",
      name: `GET /api/accounting/property/${propertyId}`,
    },
    async () => {
      const response = await fetch(`/api/accounting/property/${propertyId}`);
      return response.json();
    },
  );
}
```

### Structured Logging

Enable structured logging in Sentry initialization and use throughout the application:

#### Configuration

```javascript
import * as Sentry from "@sentry/react";

Sentry.init({
  dsn: import.meta.env.VITE_SENTRY_DSN,
  enableLogs: true,
  integrations: [
    Sentry.consoleLoggingIntegration({ 
      levels: ["log", "error", "warn"] 
    }),
    Sentry.browserTracingIntegration(),
    Sentry.replayIntegration(),
  ],
});
```

#### Business Context Logging Examples

```javascript
const { logger } = Sentry;

// Property Management
logger.trace("Starting property creation", { 
  propertyType: "apartment", 
  userId: currentUser.id 
});
logger.info("Property created successfully", { 
  propertyId: "prop_123", 
  unitCount: 24,
  landlordId: "user_456"
});

// Financial Operations
logger.info("Invoice generated", { 
  invoiceId: "inv_789", 
  amount: 1200,
  tenantId: "tenant_101",
  propertyId: "prop_123"
});
logger.warn("Payment overdue", { 
  tenantId: "tenant_202", 
  daysPastDue: 15,
  amountOwed: 1800,
  propertyAddress: "123 Main St"
});

// Error Scenarios
logger.error("QuickBooks sync failed", {
  error: error.message,
  propertyId: "prop_123",
  syncType: "invoice_export",
  retryCount: 3
});
logger.fatal("Database connection pool exhausted", {
  database: "properties",
  activeConnections: 100,
  maxConnections: 100
});
```

### Integration Requirements

- **Initialization**: Sentry must be first import in `Frontend/src/index.jsx`
- **Error Boundaries**: All error boundaries include Sentry reporting with business context
- **Performance Monitoring**: Critical user flows (property creation, payment processing, QuickBooks sync)
- **Structured Logging**: Business-critical operations with relevant context
- **Environment Variables**: `VITE_SENTRY_DSN` and `SENTRY_AUTH_TOKEN` properly configured
