from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
import logging
from starlette.middleware.base import BaseHTTPMiddleware

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.info("🚀 Booting FastAPI app...")

app = FastAPI()

# CORS Configuration
origins = [
    "http://localhost:5173",
    "https://app.brikli.com",
    "https://brikli.azurewebsites.net",
    "https://lemon-island-038ac790f.6.azurestaticapps.net",
    "https://icy-glacier-00294140f6.azurestaticapps.net",  # Staging frontend
    "https://brikli-staging.azurewebsites.net"  # Staging frontend
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Custom middleware to handle X-Forwarded-Proto header from Azure's proxy
class ProxyHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        forwarded_proto = request.headers.get("X-Forwarded-Proto")
        if forwarded_proto:
            request.scope["scheme"] = forwarded_proto
        return await call_next(request)

# Azure App Service runs behind a proxy, so we need to:
# 1. Trust X-Forwarded-* headers to ensure the app knows requests are HTTPS
# 2. Add host validation for security (optional but recommended)
# This prevents 307 redirects to HTTP and mixed content errors
logger.info("🔒 Adding security middleware for HTTPS enforcement...")

# Make FastAPI respect the X-Forwarded-Proto header from Azure's proxy
app.add_middleware(ProxyHeadersMiddleware)

# Optional: Validate Host headers for security
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"])

# Router import + error trapping
try:
    # Router Imports
    from Backend.api.auth import router as auth_router
    from Backend.api.properties import router as properties_router
    from Backend.api.dashboard import router as dashboard_router
    from Backend.api.vendors import router as vendors_router
    from Backend.api.leases import router as leases_router
    from Backend.api.accounting import router as accounting_router
    from Backend.api.communication import router as communication_router
    from Backend.api.ai import router as ai_router
    from Backend.api.tenants import router as tenants_router
    from Backend.api.rent_tracker import router as rent_tracker_router
    from Backend.api.units import router as units_router
    from Backend.api.reports import router as reports_router
    from Backend.api.health import router as health_router


    app.include_router(auth_router, prefix="/api") 
    app.include_router(properties_router, prefix="/api")
    app.include_router(dashboard_router, prefix="/api")
    app.include_router(vendors_router, prefix="/api")
    app.include_router(leases_router, prefix="/api")
    app.include_router(accounting_router, prefix="/api")
    app.include_router(communication_router, prefix="/api")
    app.include_router(ai_router, prefix="/api")
    app.include_router(tenants_router, prefix="/api")
    app.include_router(rent_tracker_router, prefix="/api")
    app.include_router(units_router, prefix="/api")
    app.include_router(reports_router, prefix="/api")
    app.include_router(health_router, prefix="")  # No prefix so it's available at /ping directly


    logger.info("✅ Routers mounted successfully.")
except Exception as e:
    logger.exception("❌ Failed to mount routers:")
    raise

# Add back root and health check endpoints if desired
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

# --- Ensure initialization logic is still present ---
# Load environment variables at startup (assuming this logic was previously working)
# If you had find_dotenv() and load_dotenv() logic here before, re-add it.
# Initialize all models before creating the FastAPI app
# (Assuming this import handles SQLAlchemy/SQLModel setup)
import Backend.models

# --- End of Ensure initialization logic ---

logger.info("🚀 FastAPI app initialization complete.")