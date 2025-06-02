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
- **AI**: Azure OpenAI (for lease parsing and future features)
- **Storage**: Azure Blob Storage (for lease documents, avatars, etc.)

---

## 🛠️ Local Development Setup

### 1. Clone the repo

```bash
git clone https://github.com/Brikli-Property-Management/Brikli-V2.git
cd Brikli-V2
```

### 2. Environment Variables

Create a `.env` file in your root directory and one in your Frontend/ folder. Refer to the #private-keys channel on Slack for the contents of both, and shoot me a message for the protected keys.

### 3. Starting up local Backend

```bash

pip install poetry #If you don't already have Poetry installed
poetry install # Installs dependencies from poetry.lock

# Run the backend server
poetry run uvicorn Backend.api.app:app --reload
```

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

## Database Migrations (Alembic)

Database schema changes are managed using Alembic.

- **Ensure `Backend/.env` `DATABASE_URL` is correct before running Alembic commands.**
- Alembic's `env.py` is configured to use `DATABASE_URL`.

To create a new migration:

```bash

poetry run alembic revision -m "your_migration_message"
```

Edit the generated script in `Backend/migrations/versions/`.

To apply migrations:

```bash
poetry run alembic upgrade head
```

To downgrade:

```bash

poetry run alembic downgrade -1 # Downgrade one revision
```

---

## 🚀 Deployment

### Porter Deployment (Backend)

The backend is deployed to Porter using a Docker container.

**Automated Deployment**

- Push to `main` branch, triggers the "Deploy to brikli-backend-prod" GitHub Actions workflow which uses the "porter_app_brikli-backend-prod_4829.yml" workflow file in the .github\workflows folder.

- The workflow automatically copies the Poetry files (`pyproject.toml`, `poetry.lock`) from the root to the `Backend/` directory before building the Docker image.
- Porter builds and deploys the Docker container.

**Manual Deployment**
If deploying manually through Porter UI or CLI:

1. Ensure the `pyproject.toml` and `poetry.lock` in the `Backend/` directory are up-to-date (sync from root if needed).
   ```bash
   # On Windows
   # ./sync-poetry-files.ps1
   # On macOS/Linux
   # ./sync-poetry-files.sh
   ```
2. Deploy using Porter, ensuring it uses the Dockerfile in `Backend/`.

Deployment configurations (example for Porter):

- Application root path: `/Backend` (relative to where Porter checks out the repo)
- Dockerfile path: `Backend/Dockerfile` (relative to repo root)
- Start command (from Dockerfile): `gunicorn -w 2 -k uvicorn.workers.UvicornWorker Backend.api.app:app`

### Frontend Deployment

#### CURRENTLY NOT DEPLOYED

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
