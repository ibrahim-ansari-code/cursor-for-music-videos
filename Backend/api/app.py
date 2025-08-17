import logging
import sys
from pathlib import Path

# Add project root to Python path for proper module imports
# This ensures Backend.* imports work when running from Backend/ directory
project_root = Path(__file__).resolve().parents[2]  # Go up from api/app.py to project root
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))  # pragma: no cover

from fastapi import APIRouter, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import status

# Configure clean logging
def setup_logging():
    """Configure logging with cleaner output and better error visibility"""
    
    # Root logger configuration
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
        datefmt='%H:%M:%S',
        stream=sys.stdout
    )
    
    # Reduce noise from external libraries
    logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
    logging.getLogger('sqlalchemy.dialects').setLevel(logging.WARNING)
    logging.getLogger('sqlalchemy.pool').setLevel(logging.WARNING)
    logging.getLogger('sqlalchemy.orm').setLevel(logging.WARNING)
    logging.getLogger('httpx').setLevel(logging.WARNING)  # Reduce Supabase auth noise
    
    # Keep our application logs visible
    logging.getLogger('Backend').setLevel(logging.INFO)
    logging.getLogger('uvicorn.access').setLevel(logging.WARNING)
    
    # Enable SQL logging only when explicitly requested via environment variable
    import os
    if os.getenv('SQL_DEBUG', '').lower() in ('true', '1', 'yes'):
        logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
        logging.getLogger(__name__).info("🔍 SQL_DEBUG enabled - SQL queries will be logged")

setup_logging()
logger = logging.getLogger(__name__)
logger.info("🚀 Booting FastAPI app...")

app = FastAPI()
api_main_router = APIRouter()

# CORS Configuration with regex support for dynamic preview URLs
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "https://localhost:5173",
        "http://localhost:5174",
        "https://localhost:5174",
        "http://127.0.0.1:5173",
        "https://127.0.0.1:5173",
        "http://tenant.brikli.com",
        "https://tenant.brikli.com",
        "http://app.brikli.com",
        "https://app.brikli.com",
        "http://api.brikli.com",
        "https://brikli-api-8919-151e4fdf-aa5gqdc5.onporter.run",
        "https://brikli-api-8919-7953fd68-fofj7ysk.onporter.run"
    ],
    # Allow any Porter preview environment URL
    allow_origin_regex=r"https://.*\.onporter\.run",
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
        "brikli.com",
        "api.brikli.com",
        "brikli.azurewebsites.net",
        "localhost",
        "brikli-api-8919-7953fd68-fofj7ysk.onporter.run",
        "brikli-api-8919-151e4fdf-aa5gqdc5.onporter.run",
        "*.onporter.run",  # Allow all Porter preview environments
    ]
)

# Add the RequestValidationError handler here


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Handles request validation errors by returning a JSON response with formatted error details.
    
    Converts FastAPI validation errors into a JSON-serializable structure, including location, message, type, and optional input and context fields, and responds with HTTP 422 status.
    """
    # Log the original error for debugging
    logger.error("❌ Validation error for %s: %s", request.url.path, exc.errors())

    # Convert validation errors to a JSON-serializable format
    serializable_errors = []
    for error in exc.errors():
        serializable_error = {
            "loc": list(error.get("loc", [])),
            "msg": str(error.get("msg", "")),  # Ensure msg is a string
            "type": error.get("type", ""),
        }
        # Safely include 'input'
        if "input" in error:
            inp = error["input"]
            if isinstance(inp, (str, int, float, bool, type(None))):
                serializable_error["input"] = inp
            else:
                serializable_error["input"] = str(inp)

        # Safely include 'ctx' by converting it to a string
        if "ctx" in error:
            serializable_error["ctx"] = str(error["ctx"])

        serializable_errors.append(serializable_error)

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": serializable_errors},
    )

# Router import + error trapping
try:
    # Router Imports
    from Backend.api.accounting import accounting_api_router
    from Backend.api.agent import router as agent_router
    from Backend.api.auth import router as auth_router
    from Backend.api.dashboard import router as dashboard_router
    from Backend.api.health import router as health_router
    from Backend.api.leases.router import router as leases_router
    from Backend.api.properties.router import router as properties_router
    from Backend.api.reports import router as reports_router
    from Backend.api.tenants.router import router as tenants_router
    from Backend.api.units.router import router as units_router
    from Backend.api.maintenance.router import router as maintenance_router
    from Backend.api.quickbooks.router import router as quickbooks_router

    # Include routers into the central api_main_router
    # Their internal prefixes (e.g., /auth, /properties) will apply
    api_main_router.include_router(auth_router)
    api_main_router.include_router(properties_router)
    api_main_router.include_router(dashboard_router)
    api_main_router.include_router(leases_router)
    # Include the new accounting router with its own base prefix
    api_main_router.include_router(accounting_api_router, prefix="/accounting")
    api_main_router.include_router(agent_router)
    api_main_router.include_router(tenants_router)
    api_main_router.include_router(units_router)
    api_main_router.include_router(reports_router)
    api_main_router.include_router(health_router)
    api_main_router.include_router(maintenance_router)
    api_main_router.include_router(quickbooks_router, prefix="/quickbooks", tags=["QuickBooks"])

    # Define the /api/health endpoint on the api_main_router
    @api_main_router.get("/health")
    async def api_health_check():
        """Health check endpoint for the API, available at /api/health"""
        logger.info("✅ Health check - API is healthy")
        return {
            "status": "ok",
            "message": "API is healthy"
        }

    # Mount the central API router to the app with /api prefix
    app.include_router(api_main_router, prefix="/api")

    logger.info("✅ Routers mounted successfully under /api prefix.")
except Exception as e:
    logger.exception("❌ Failed to mount routers: %s", e)
    raise

# Root endpoint (remains on app, not under /api)


@app.get("/")
def root():
    return {"message": "Brikli backend is running"}


# Initialize all models before creating the FastAPI app

logger.info("🚀 FastAPI app initialization complete.")
