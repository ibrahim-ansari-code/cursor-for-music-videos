from fastapi import FastAPI, Request, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.info("🚀 Booting FastAPI app...")

app = FastAPI()
api_main_router = APIRouter()

# CORS Configuration
origins = [
    "http://localhost:5173",
    "https://app.brikli.com",
    "https://brikli.azurewebsites.net",
    "https://lemon-island-038ac790f.6.azurestaticapps.net",
    "https://icy-glacier-00294140f.6.azurestaticapps.net", # Corrected Staging frontend
    "https://brikli-staging.azurewebsites.net",
    "http://brikli-staging.azurewebsites.net",
    "https://thankful-pond-068620f0f.6.azurestaticapps.net"
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
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=[
        "app.brikli.com",
        "brikli.azurewebsites.net",
        "localhost",
        "brikli-staging.azurewebsites.net",
        "icy-glacier-00294140f.6.azurestaticapps.net", # Staging frontend
        "thankful-pond-068620f0f.6.azurestaticapps.net"  # Production frontend, if different from app.brikli.com
    ]
)

# Add the RequestValidationError handler here
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.error(f"Validation error: {exc.errors()} for request: {request.url} with body: {exc.body}")
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors(), "body": exc.body},
    )

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

    # Include routers into the central api_main_router
    # Their internal prefixes (e.g., /auth, /properties) will apply
    api_main_router.include_router(auth_router)
    api_main_router.include_router(properties_router)
    api_main_router.include_router(dashboard_router)
    api_main_router.include_router(vendors_router)
    api_main_router.include_router(leases_router)
    api_main_router.include_router(accounting_router)
    api_main_router.include_router(communication_router)
    api_main_router.include_router(ai_router)
    api_main_router.include_router(tenants_router)
    api_main_router.include_router(rent_tracker_router)
    api_main_router.include_router(units_router)
    api_main_router.include_router(reports_router)
    api_main_router.include_router(health_router)

    # Define the /api/health endpoint on the api_main_router
    @api_main_router.get("/health")
    async def api_health_check():
        """Health check endpoint for the API, available at /api/health"""
        logger.info("HEALTH CHECK ENDPOINT HIT - /api/health")
        return {
            "status": "ok",
            "message": "API is healthy"
        }

    # Mount the central API router to the app with /api prefix
    app.include_router(api_main_router, prefix="/api")

    logger.info("✅ Routers mounted successfully under /api prefix.")
except Exception as e:
    logger.exception("❌ Failed to mount routers:")
    raise

# Root endpoint (remains on app, not under /api)
@app.get("/")
def root():
    return {"message": "Brikli backend is running"}

# --- Ensure initialization logic is still present ---
# Load environment variables at startup (assuming this logic was previously working)
# If you had find_dotenv() and load_dotenv() logic here before, re-add it.
# Initialize all models before creating the FastAPI app
# (Assuming this import handles SQLAlchemy/SQLModel setup)
import Backend.models

# --- End of Ensure initialization logic ---

logger.info("🚀 FastAPI app initialization complete.")