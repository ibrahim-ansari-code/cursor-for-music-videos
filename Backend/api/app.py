from fastapi import FastAPI
from backend.api.auth import router as auth_router
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

# Include routers
app.include_router(auth_router)

@app.get("/")
def root():
    return {"message": "Brikli backend is running"}