from fastapi import FastAPI
from Backend.api.auth import router as auth_router
from Backend.api.vendors import router as vendors_router
from Backend.api.leases import router as leases_router
from Backend.api.accounting import router as accounting_router
from Backend.api.dashboard import router as dashboard_router
from Backend.api.communication import router as communication_router
from Backend.api.ai import router as ai_router
from Backend.api.properties import router as properties_router
from Backend.api.tenants import router as tenants_router
from dotenv import load_dotenv, find_dotenv
from fastapi.middleware.cors import CORSMiddleware
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables at startup
def load_environment():
    """Load environment variables at application startup."""
    try:
        env_path = find_dotenv()
        if env_path:
            logger.info(f"Loading environment variables from: {env_path}")
            load_dotenv(env_path)
        else:
            logger.warning("No .env file found in current or parent directories")
    except Exception as e:
        logger.error(f"Error loading .env file: {str(e)}")
        raise

# Load environment variables
load_environment()

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
app.include_router(tenants_router, prefix="/api")

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