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
- **Dev DB**: SQLite  
- **Cloud DB (planned)**: Azure SQL  

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
.env\Scriptsctivate       # Windows
# source venv/bin/activate    # macOS/Linux

pip install poetry
poetry install --no-root

poetry run uvicorn app:app --reload --app-dir ./api
```

Runs at `http://localhost:8000`  
FastAPI docs available at `http://localhost:8000/docs`

---