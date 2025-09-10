# Logging Configuration & Debugging Fixes

This document explains the improved logging setup for the Brikli backend and recent issues resolved.

## Overview

The backend now uses a clean, structured logging configuration that:

- ✅ Reduces noise from external libraries (SQLAlchemy, httpx, etc.)
- ✅ Makes application logs more visible
- ✅ Uses consistent formatting with timestamps
- ✅ Makes errors easier to spot with emojis and clear formatting
- ✅ Allows verbose debugging when needed

## Recent Issues Fixed (June 2025)

### 🔧 **Pydantic Schema Error**

**Problem**: `LeaseResponse` schema had unresolved forward references causing validation errors.
**Solution**: Fixed by properly importing `Tenant` and `Property` models and calling `LeaseResponse.model_rebuild()`.

### 🔧 **Frontend Auth Loop**

**Problem**: Multiple concurrent auth calls (`auth/v1/user`) causing 307 redirects and performance issues.
**Solution**: Removed `allLeases` from useEffect dependency array in `Tenants.jsx` to prevent infinite re-renders.

### 🔧 **Log Noise Reduction**

**Problem**: SQLAlchemy and httpx logs flooding the terminal, making errors impossible to spot.
**Solution**: Set external libraries to WARNING level while keeping Backend logs at INFO level.

## Default Behavior

By default, the application will:

- Show INFO level logs for our Backend modules
- Hide SQLAlchemy query logs (previously flooding the output)
- Hide Supabase auth calls (httpx) to reduce noise
- Show WARNING level and above for external libraries
- Use a clean format: `HH:MM:SS | LEVEL | MODULE | MESSAGE`

## Enabling SQL Debug Mode

When you need to see SQL queries for debugging, set the `SQL_DEBUG` environment variable:

```bash
# Enable SQL query logging
export SQL_DEBUG=true
poetry run uvicorn Backend.api.app:app --reload

# Or for one command
SQL_DEBUG=true poetry run uvicorn Backend.api.app:app --reload
```

This will show all SQL queries and their parameters, similar to the old behavior.

## Log Levels

- `ERROR` ❌ - Critical errors that need immediate attention
- `WARNING` ⚠️  - Important issues that should be addressed
- `INFO` ℹ️   - General application flow and important events
- `DEBUG` 🔍  - Detailed information for debugging (when SQL_DEBUG=true)

## Example Output

### Normal Operation (Clean)

```text
18:38:35 | INFO     | Backend.api.app | 🚀 Booting FastAPI app...
18:38:35 | INFO     | Backend.database | Preparing to create async engine...
18:38:35 | INFO     | Backend.api.leases.service | Fetching leases for user 123...
18:38:35 | INFO     | Backend.api.leases.service | Successfully fetched 5 leases
```

### With SQL_DEBUG=true (Verbose)

```text
18:38:35 | INFO     | Backend.api.app | 🔍 SQL_DEBUG enabled - SQL queries will be logged
18:38:35 | INFO     | sqlalchemy.engine | SELECT * FROM leases WHERE...
```

### Error Example

```text
18:38:35 | ERROR    | Backend.api.leases.service | ❌ Error fetching leases for user 123: Invalid property ID
```

## Libraries with Reduced Logging

These libraries are set to WARNING level to reduce noise:

- `sqlalchemy.engine` - Database query logs
- `sqlalchemy.dialects` - SQL dialect logs  
- `sqlalchemy.pool` - Connection pool logs
- `sqlalchemy.orm` - ORM logs
- `httpx` - HTTP client logs (Supabase auth calls)
- `uvicorn.access` - HTTP access logs

This makes it much easier to identify actual problems without being overwhelmed by routine operational logs.
