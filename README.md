# Brikli-V2

Brikli is a property management platform built from the ground up for clarity, scalability, and AI augmentation.

---

## 🗂️ Project Structure

```text
Brikli-V2/
├── Backend/         # FastAPI backend (unified for both frontends)
├── Frontend/        # Property management frontend (React + Vite + Tailwind)
└── Tenant-Frontend/ # Tenant portal frontend (React + Vite + Tailwind)
```

---

## ⚙️ Tech Stack

- **Frontend**: React 18, Vite, Tailwind CSS, React Router v7
- **Backend**: FastAPI (Python 3.11+), SQLModel, Async PostgreSQL with SQLAlchemy
- **Database**: Supabase PostgreSQL (primary), Azure PostgreSQL (legacy/phasing out)
- **Database Migrations**: Supabase CLI with database branching
- **Auth**: Supabase JWT with user sync
- **Integrations**: Apideck (QuickBooks), OpenAI (AI-powered receipt parsing)
- **Storage**: Azure Blob Storage (receipts, documents, avatars)

---

## 📚 Documentation

- **[Frontend Architecture](Frontend/ARCHITECTURE.md)**: Detailed documentation of frontend patterns, shared components, and architectural decisions including the shared receipt upload pattern.

---

## 🛠️ Local Development Setup

### 1. Clone the repo

```bash
git clone https://github.com/Brikli-Property-Management/Brikli-V2.git
cd Brikli-V2
```

### 2. Environment Variables

Create a `.env` file in your Backend/, Frontend/, and Tenant-Frontend/ directories. Refer to the #private-keys channel on Slack for the contents and shoot Zubin (<zubin.singh@brikli.com>) a message for the protected keys.

### 3. Installing Backend Dependencies and Running Local Backend

```bash
pip install poetry #If you don't already have Poetry installed

# Navigate to Backend directory
cd Backend

poetry install # Installs dependencies from poetry.lock

# Run the backend server
# For Unix/Linux/macOS (bash):
poetry run uvicorn api.app:app --reload

# For Windows PowerShell:
poetry run uvicorn api.app:app --reload
```

**Important:**

- Make sure you have a `.env` file in the `Backend/` directory with your `DATABASE_URL` and other required environment variables
- The server will start at `http://localhost:8000` with API docs at `http://localhost:8000/docs`

Backend runs at `http://localhost:8000`.
FastAPI docs available at `http://localhost:8000/docs`.

### 4. Start up local Frontends

**Property Management Frontend:**

```bash
cd Frontend
npm install
npm run dev
```

**Tenant Portal Frontend:**

```bash
cd Tenant-Frontend
npm install
npm run dev
```

- Property Management Frontend runs at `http://localhost:5173`
- Tenant Portal Frontend runs at `http://localhost:5174`

---

## Database Migrations (Supabase CLI + DB Branching)

⚠️ **IMPORTANT: Alembic is decommissioned and should NOT be used.**

All database schema changes are now managed exclusively through Supabase local development with Supabase CLI and database branching.

### Migration Workflow

1. **Create a database branch** for your feature development
2. **Make schema changes** using Supabase Studio or direct SQL
3. **Generate migration file** to capture your changes
4. **Commit the migration file** in your PR
5. **Changes are automatically applied** to production when the PR is merged

### Commands

```bash
# Generate a migration file after making schema changes
supabase db diff --use-migra -f migration_name

# Apply migrations locally
supabase db push

# Reset your local database (if needed)
supabase db reset
```

**Migration files are located in `supabase/migrations/` and must be committed to version control.**

---

## 🧪 Testing

### Prerequisites for Testing

- Backend server must be running at `http://localhost:8000`
- Valid `.test_credentials.json` file in `Backend/tests/` directory
- Environment variables configured in `.env` files

### Running Tests

```bash
cd Backend/tests

# Run all API tests
python run_all_api_tests_pytest.py

# Run specific test suites
python -m pytest api_tests/ -v
python -m pytest integration_tests/ -v
python -m pytest unit_tests/ -v
```

---

## 🚀 Deployment

### Branching Strategy & CI/CD

The project follows a `feature -> main` branching strategy:

1. **Feature Branches**: All new features and bug fixes are developed in `feature/*` branches.
2. **Main Branch (`main`)**: Feature branches are merged directly into `main` via Pull Requests, which represents the production-ready state.

### Porter Deployment (Backend & Frontends)

The backend, property management frontend, and tenant portal frontend are all deployed to the same cluster on **Porter**.

- **Production Deployment**: A push to the `main` branch automatically triggers the respective production deployment workflows on Porter for the backend, property management frontend, and tenant portal frontend.
- **Preview Environments**: When a Pull Request is opened against the `main` branch, Porter automatically spins up **preview environments** for all three applications (`brikli-backend-prod`, `brikli-frontend-prod`, `brikli-tenant-frontend-prod`). This allows for comprehensive, on-cluster testing of changes before they are merged into production.

---

## 📝 Backend API Usage Example

The `get_session()` function can be used as a FastAPI dependency in your route handlers like this:

```python
from fastapi import Depends
from sqlmodel.ext.asyncio.session import AsyncSession
# Assuming get_session is in Backend.database
from Backend.database import get_session

@router.get("/items") # Assuming 'router' is your APIRouter instance
async def get_items(session: AsyncSession = Depends(get_session)):
    # Use the session here
    pass
```
