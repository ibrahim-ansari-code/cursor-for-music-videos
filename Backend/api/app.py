from fastapi import FastAPI
from Backend.api.auth import router as auth_router
from Backend.api.vendors import router as vendors_router
from Backend.api.leases import router as leases_router
from Backend.api.accounting import router as accounting_router
from Backend.api.dashboard import router as dashboard_router
from Backend.api.communication import router as communication_router
from Backend.api.ai import router as ai_router
from Backend.api.properties import router as properties_router
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware


load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router, prefix="/api")
app.include_router(vendors_router, prefix="/api")
app.include_router(leases_router, prefix="/api")
app.include_router(accounting_router, prefix="/api")
app.include_router(dashboard_router, prefix="/api")
app.include_router(communication_router, prefix="/api")
app.include_router(ai_router, prefix="/api")
app.include_router(properties_router, prefix="/api")

@app.get("/")
def root():
    return {"message": "Brikli backend is running"}

@app.get("/api/health")
async def health():
    """Health check endpoint for the API"""
    return {
        "status": "ok",
        "message": "API is healthy"
    }