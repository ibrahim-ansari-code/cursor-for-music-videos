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

## 🛠️ Local Setup

### 1. Clone the repo

```bash
git clone https://github.com/YOUR_ORG/Brikli-V2.git
cd Brikli-V2
```

### 2. Environment Variables
Create a `.env` file in the `Backend/` directory. Refer to `.env.example` (if one exists) or `Backend/config.py` for required variables. Key variables include:
- `DATABASE_URL`: Your Supabase PostgreSQL connection string (e.g., `postgresql+asyncpg://postgres:[YOUR-PASSWORD]@[YOUR-SUPABASE-HOST]:5432/postgres`)
- `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_DEPLOYMENT`, `AZURE_OPENAI_API_VERSION`
- `AZURE_STORAGE_CONNECTION_STRING`, `AZURE_BLOB_PUBLIC_URL`
- `SUPABASE_URL`, `SUPABASE_KEY` (for frontend Supabase client) - usually in `Frontend/.env`

For the frontend, create a `.env` file in the `Frontend/` directory:
- `VITE_SUPABASE_URL="your_supabase_project_url"`
- `VITE_SUPABASE_ANON_KEY="your_supabase_anon_key"`
- `VITE_API_URL="http://localhost:8000"` (or your backend URL)
- `VITE_AZURE_MAPS_KEY="your_azure_maps_key"`

### 3. Backend

```bash
cd Backend
python -m venv venv
# Activate virtual environment
# Windows:
# .venv\Scripts\activate
# macOS/Linux:
# source venv/bin/activate

pip install poetry
poetry install --no-root # Installs dependencies from poetry.lock

# Apply database migrations (run from Backend directory)
# Ensure your .env file has the correct DATABASE_URL for Supabase
poetry run alembic upgrade head

# Run the backend server
poetry run uvicorn Backend.api.app:app --reload --host 0.0.0.0 --port 8000
```

Backend runs at `http://localhost:8000`.
FastAPI docs available at `http://localhost:8000/docs`.

### 4. Frontend

```bash
cd Frontend
npm install
npm run dev
```

Frontend runs at `http://localhost:5173` (or as specified by Vite).

---

## Database Migrations (Alembic)

Database schema changes are managed using Alembic.

- **Ensure `Backend/.env` `DATABASE_URL` is correct before running Alembic commands.**
- Alembic's `env.py` is configured to use this `DATABASE_URL`.

To create a new migration:
```bash

poetry run alembic revision -m "your_migration_message"
```
Edit the generated script in `Backend/migrations/versions/`.

To apply migrations:
```bash
cd Backend
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
- Push to `main` branch triggers a GitHub Actions workflow.
- The workflow automatically copies the Poetry files (`pyproject.toml`, `poetry.lock`) from the root to the `Backend/` directory before building the Docker image.
- Porter builds and deploys the Docker container.
- **Important**: Ensure production environment variables (especially `DATABASE_URL` for Supabase) are correctly configured in Porter.

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
- Start command (from Dockerfile): `gunicorn -w 4 -k uvicorn.workers.UvicornWorker Backend.api.app:app --bind 0.0.0.0:8080 --timeout 300` (Port may vary based on Porter setup)

### Frontend Deployment
The frontend is typically deployed as a static site (e.g., Azure Static Web Apps, Vercel, Netlify).
- Build command: `npm run build` (from `Frontend/` directory)
- Output directory: `Frontend/dist`
- Ensure production environment variables (like `VITE_API_URL` pointing to the deployed backend, `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`) are set during the build process or in the hosting service.

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