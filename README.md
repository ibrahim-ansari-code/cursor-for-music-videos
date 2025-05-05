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
- **Auth**: OAuth2 with JWT  
- **DB**: Azure PostgreSQL & Supabase PostgreSQL

---

## 🛠️ Local Setup

### 1. Clone the repo

```bash
git clone https://github.com/YOUR_ORG/Brikli-V2.git
cd Brikli-V2
```

---

### 2. Frontend

```bash
cd Frontend
npm install
npm run dev
```

Runs at `http://localhost:5173`

---

### 3. Backend

```bash
cd Backend
python -m venv venv
.venv\Scripts\activate       # Windows
# source venv/bin/activate    # macOS/Linux

pip install poetry
poetry install --no-root

poetry run uvicorn Backend.api.app:app --reload
```

Runs at `http://localhost:8000`  
FastAPI docs available at `http://localhost:8000/docs`

---

## 📝 Usage

The `get_session()` function can be used as a FastAPI dependency in your route handlers like this:

```python
from fastapi import Depends
from sqlmodel.ext.asyncio.session import AsyncSession

@app.get("/items")
async def get_items(session: AsyncSession = Depends(get_session)):
    # Use the session here
    pass
```