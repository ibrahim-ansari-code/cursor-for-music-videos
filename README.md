# Brikli-V2

Brikli is a property management platform rebuilt from the ground up for clarity, scalability, and AI augmentation. This repository contains the new version of the app with a clean separation between frontend and backend.

---

## 🗂️ Project Structure

```
Brikli-V2/
├── Backend/      # FastAPI backend
└── Frontend/     # React + Vite + Tailwind frontend
```

---

## ⚙️ Tech Stack

- **Frontend**: React, Vite, Tailwind CSS
- **Backend**: FastAPI (Python 3.11+)
- **ORM**: SQLModel
- **Database Migration**: Alembic
- **Auth**: Supabase Auth (handles JWTs)
- **DB**: Supabase PostgreSQL (primary), Azure PostgreSQL (legacy/phasing out)
- **Integrations**: Apideck (for QuickBooks Online)
- **AI**: Azure OpenAI (for lease parsing and future features)
- **Storage**: Azure Blob Storage (for lease documents, avatars, etc.)

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

Create a `.env` file in your root directory and one in your Frontend/ folder. Refer to the #private-keys channel on Slack for the contents of both, and shoot Zubin (zubin.singh@brikli.com) a message for the protected keys.

### 3. Installing Backend Dependencies and Running Local Backend

```bash
pip install poetry #If you don't already have Poetry installed

# Navigate to Backend directory
cd Backend

poetry install # Installs dependencies from poetry.lock

# Run the backend server
# For Unix/Linux/macOS (bash):
PYTHONPATH=.. poetry run uvicorn Backend.api.app:app --reload

# For Windows PowerShell:
$env:PYTHONPATH=".." ; poetry run uvicorn Backend.api.app:app --reload
```

**Important:** 
- Make sure you have a `.env` file in the `Backend/` directory with your `DATABASE_URL` and other required environment variables
- The server will start at `http://localhost:8000` with API docs at `http://localhost:8000/docs`

Backend runs at `http://localhost:8000`.
FastAPI docs available at `http://localhost:8000/docs`.

### 4. Start up local Frontend

```bash
cd Frontend
npm install
npm run dev
```

Frontend runs at `http://localhost:5173` by default.

---

## Database Migrations (Supabase MCP + Alembic)

Database schema changes are made individually using Supabase MCP on a new DB Branch and are sync'd and managed using Alembic. This workflow ensures that direct schema changes in the Supabase UI can be captured and version-controlled as migration scripts.

- **Ensure `Backend/.env` `DATABASE_URL` is correct before running Alembic commands.**
- Alembic's `env.py` is configured to use `DATABASE_URL`.

To create a new migration:

```bash
# From the Backend directory
cd Backend
poetry run alembic revision --autogenerate -m "your_migration_message"
```

Edit the generated script in `migrations/versions/`.

To apply migrations:

```bash
# From the Backend directory  
cd Backend
poetry run alembic upgrade head
```

To downgrade:

```bash
# From the Backend directory
cd Backend  
poetry run alembic downgrade -1 # Downgrade one revision
```

---

## 🚀 Deployment

### Branching Strategy & CI/CD

The project follows a `feature -> dev -> main` branching strategy:

1.  **Feature Branches**: All new features and bug fixes are developed in `feature/*` branches.
2.  **Development Branch (`dev`)**: Completed features are merged into the `dev` branch for consolidation and integration testing.
3.  **Main Branch (`main`)**: After the `dev` branch is stable, it is merged into `main`, which represents the production-ready state.

### Porter Deployment (Backend & Frontend)

Both the frontend and backend are deployed to the same cluster on **Porter**.

-   **Production Deployment**: A push to the `main` branch automatically triggers the respective production deployment workflows on Porter for both the frontend and backend.
-   **Preview Environments**: When a Pull Request is opened against the `main` branch, Porter automatically spins up **preview environments** for both the frontend (`brikli-frontend-prod`) and backend (`brikli-backend-prod`). This allows for comprehensive, on-cluster testing of changes before they are merged into production.

The backend deployment workflow includes a step to copy the root `pyproject.toml` and `poetry.lock` files into the `Backend/` directory to ensure the Docker build has the correct dependencies.

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
