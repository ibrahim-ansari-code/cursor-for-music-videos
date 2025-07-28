# Brikli Tenant Portal: Architectural Decision Record (ADR)

This document outlines the key architectural and setup decisions for the Brikli Tenant Portal. It is intended to be a living document that serves as a single source of truth for development.

## 1. High-Level Architecture: Monorepo & Shared Backend

The most significant architectural decision is to build the Tenant Portal as part of the existing `Brikli-V2` monorepo, rather than creating a separate, siloed project.

- **What:** The Tenant Portal will be a new, independent frontend application (`Tenant-Frontend/`) that coexists with the Landlord Portal (`Frontend/`). Both frontends will be served by the **same, extended backend application** (`Backend/`).
- **Why:** This approach was chosen for several key reasons:
    - **Efficiency & Code Reuse:** It avoids duplicating backend logic, database connections, and authentication systems. We leverage the existing, robust FastAPI backend.
    - **Single Source of Truth:** All data (users, leases, properties, maintenance requests) resides in a single Supabase database. This eliminates the massive complexity and risk of data synchronization issues between two separate systems.
    - **Simplified Authentication:** We will use the **single, existing Supabase authentication** system for both landlords and tenants. This simplifies user management and security.
    - **Scalability:** It positions the Brikli platform as a true multi-tenant application, making it easier to add new roles or portals (e.g., a Staff Portal) in the future.

## 2. Project Structure & Dependency Management

To support the monorepo architecture, we performed a critical restructuring of the backend's dependency management.

- **What:** `pyproject.toml`, `poetry.lock`, and `alembic.ini` were moved from the root directory into the `Backend/` directory. The `.env` file was also moved into `Backend/`.
- **Why:**
    - **Encapsulation:** This makes the `Backend/` application a self-contained, independent Python project.
    - **Clarity:** It clearly delineates backend dependencies from any potential root-level or frontend tooling.
    - **Standard Practice:** This is the standard and recommended way to structure Python projects within a larger monorepo.

## 3. CI/CD & Deployment Adjustments

The restructuring required updates to our CI/CD pipelines to ensure deployments remain functional.

- **What:**
    - The Porter build context for the backend was confirmed to be `./Backend`, meaning the `Dockerfile` works correctly without changes to its `COPY` commands.
    - The GitHub Actions workflows (`test-suite.yml`, `porter*.yml`) were updated to reflect the new file locations. This primarily involved changing the working directory for `poetry` commands.
- **Why:** These changes were essential to prevent build and deployment failures after the project restructure. The pipelines now correctly understand the self-contained nature of the `Backend/` application.

## 4. Frontend Build & Development Environment Fix

We resolved a persistent, platform-specific `npm` bug on Windows that was halting frontend development.

- **What:** The issue was related to `npm`'s incorrect handling of optional dependencies for `rollup`, a sub-dependency of `vite`. The permanent fix involved:
    1.  Removing any hardcoded, platform-specific rollup binaries from `package.json`.
    2.  Adding a `postinstall` script to `package.json`.
- **Why:** This solution is robust and cross-platform.
    - The `postinstall` script intelligently checks the operating system.
    - On **Windows**, it runs `npm install @rollup/rollup-win32-x64-msvc --no-save` to fetch the necessary binary without polluting the `package.json`, fixing the local development environment.
    - On **Linux** (e.g., in the Docker container for deployment), the script does nothing, and `npm` correctly installs the appropriate Linux-native binaries for `vite`.
    - This ensures both local Windows development and production Linux deployments work seamlessly.

## 5. Development Workflow Commands

Here are the definitive commands for local development:

### Backend

```bash
# Navigate to the Backend directory
cd Backend

# Install dependencies (only needed once or when pyproject.toml changes)
poetry install

# Run the local server (from within Backend/ directory)
# For Unix/Linux/macOS (bash):
PYTHONPATH=.. poetry run uvicorn Backend.api.app:app --reload

# For Windows PowerShell:
$env:PYTHONPATH=".." ; poetry run uvicorn Backend.api.app:app --reload
```

### Frontend (Landlord Portal)

```bash
# Navigate to the Frontend directory
cd Frontend

# Install dependencies
npm install

# Run the local dev server
npm run dev
```

### Frontend (Tenant Portal)

```bash
# Navigate to the Tenant-Frontend directory
cd Tenant-Frontend

# Install dependencies
npm install

# Run the local dev server
npm run dev
```

## 6. Next Steps: Building the Tenant Portal

With the foundational work complete, the immediate plan is to set up the Tenant Portal frontend.

1.  **Initialize Project:** Install core dependencies (`react-router-dom`, `tailwindcss`, `@supabase/supabase-js`) in the `Tenant-Frontend` directory.
2.  **Scaffold UI:** Create the basic application shell, including routing for a Login Page and a placeholder Dashboard Page.
3.  **Implement Authentication:**
    - Connect to the existing Supabase instance.
    - Implement the login form and logic using `supabase.auth.signInWithPassword`.
    - Upon successful login, the backend will return a JWT. This token contains the user's `id` and `user_type`.
4.  **Role-Based Access Control (RBAC):**
    - The frontend will redirect based on the `user_type` from the JWT. If the `user_type` is not `'TENANT'`, the user should be logged out and shown an error.
    - The backend will use new authorization dependencies (`require_tenant`) to protect tenant-specific API endpoints, ensuring data security. 