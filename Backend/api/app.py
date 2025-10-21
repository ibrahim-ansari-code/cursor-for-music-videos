import logging
import sys
import json
import time
from pathlib import Path

# Add project root to Python path for proper module imports
# This ensures Backend.* imports work when running from Backend/ directory
project_root = Path(__file__).resolve().parents[2]  # Go up from api/app.py to project root
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))  # pragma: no cover

from fastapi import APIRouter, FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import status
import sentry_sdk
import os
from Backend.config import settings
from Backend.utils.datetime_utils import create_audit_datetime
from Backend.database import engine, async_session
from sqlalchemy import text

# Initialize Sentry only for production environment
sentry_dsn = os.getenv("SENTRY_DSN")
current_env = settings.ENVIRONMENT
if sentry_dsn and current_env == "production":
    sentry_sdk.init(
        dsn=sentry_dsn,
        environment=current_env,
        # Add data like request headers and IP for users,
        # see https://docs.sentry.io/platforms/python/data-management/data-collected/ for more info
        send_default_pii=False,
    )

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

# Add database connection pool monitoring and health checks
@app.on_event("startup")
async def startup_event():
    """Initialize application and verify all systems are operational."""
    logger.info("🚀 Starting FastAPI application...")
    
    # Verify database connectivity
    from Backend.database import engine, async_session
    from sqlalchemy import text
    try:
        async with async_session() as session:
            result = await session.execute(text("SELECT 1"))
            result.scalar()
        logger.info("✅ Database connection verified")
    except Exception as e:
        logger.error(f"❌ Database connection failed: {str(e)}")
        raise
    
    # Log connection pool configuration
    from Backend.database import engine
    logger.info("📊 Database pool configuration:")
    logger.info(f"  - Pool size: {engine.pool.size()}")
    logger.info(f"  - Checked out: {engine.pool.checkedout()}")
    logger.info(f"  - Checked in: {engine.pool.checkedin()}")
    logger.info(f"  - Pool status: {engine.pool.status()}")
    
    # Verify Supabase configuration (optional in CI/test environments)
    from Backend.utils.supabase import get_supabase_client
    try:
        # Test client creation (will validate environment variables)
        client = get_supabase_client()
        logger.info("✅ Supabase client configuration verified")
    except Exception as e:
        # Only fail in production - allow startup in test/CI environments
        if not settings.TESTING:
            logger.error(f"❌ Supabase configuration failed: {str(e)}")
            raise
        else:
            logger.warning(f"⚠️ Supabase configuration incomplete in test environment: {str(e)}")
            logger.info("🧪 Continuing startup in test mode without Supabase")
    
    logger.info("🚀 FastAPI application startup complete")

@app.on_event("shutdown")
async def shutdown_event():
    """Gracefully shutdown and clean up all resources."""
    logger.info("🛑 FastAPI application shutting down...")
    
    # Close HTTP session pool
    try:
        from Backend.api.quickbooks.session_manager import close_shared_session
        await close_shared_session()
        logger.info("✅ HTTP session pool closed successfully")
    except Exception as e:
        logger.error(f"⚠️ Error closing HTTP session pool: {str(e)}")
    
    # Close database connections
    from Backend.database import engine
    try:
        await engine.dispose()
        logger.info("✅ Database connections closed successfully")
    except Exception as e:
        logger.error(f"⚠️ Error closing database connections: {str(e)}")
    
    logger.info("✅ Resources cleaned up successfully")
    
    logger.info("🛑 FastAPI application shutdown complete")

# CORS Configuration with regex support for dynamic preview URLs
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "https://localhost:5173",
        "http://localhost:5174",
        "https://localhost:5174",
        "http://localhost:4173",
        "https://localhost:4173",
        "http://127.0.0.1:4173",
        "http://127.0.0.1:5173", 
        "https://127.0.0.1:5173",
        "http://[::1]:5173",
        "https://[::1]:5173",
        "http://[::1]:4173",
        "http://tenant.brikli.com",
        "https://tenant.brikli.com",
        "http://app.brikli.com",
        "https://app.brikli.com",
        "http://api.brikli.com",
        "https://brikli-api-8919-151e4fdf-aa5gqdc5.onporter.run",
        "https://brikli-api-8919-7953fd68-fofj7ysk.onporter.run"
    ],
    # Allow any Porter preview environment URL and ngrok dev tunnels
    allow_origin_regex=r"https://.*\.onporter\.run|https?://.*\.ngrok\.io|https?://.*\.ngrok-free\.app|https?://.*\.ngrok-free\.dev",
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

# Optional: Validate Host headers for security (skip in test environments)
if not settings.TESTING:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=[
            "app.brikli.com",
            "brikli.com",
            "api.brikli.com",
            "brikli.azurewebsites.net",
            "localhost",
            "127.0.0.1",
            "127.0.0.1:8000",
            "brikli-api-8919-7953fd68-fofj7ysk.onporter.run",
            "brikli-api-8919-151e4fdf-aa5gqdc5.onporter.run",
            "*.onporter.run",  # Allow all Porter preview environments
        ]
    )

#RequestValidationError handler
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
    from Backend.api.properties.image_router import router as property_images_router
    from Backend.api.reports import router as reports_router
    from Backend.api.tenants.router import router as tenants_router
    from Backend.api.tenants.documents.router import router as tenant_documents_router
    from Backend.api.tenants.documents.router import taxonomy_router as document_taxonomy_router
    from Backend.api.units.router import router as units_router
    from Backend.api.maintenance.router import router as maintenance_router
    from Backend.api.quickbooks.router import router as quickbooks_router

    # Include routers into the central api_main_router
    # Their internal prefixes (e.g., /auth, /properties) will apply
    api_main_router.include_router(auth_router)
    api_main_router.include_router(properties_router)
    api_main_router.include_router(property_images_router)
    api_main_router.include_router(dashboard_router)
    api_main_router.include_router(leases_router)
    # Include the new accounting router with its own base prefix
    api_main_router.include_router(accounting_api_router, prefix="/accounting")
    api_main_router.include_router(agent_router)
    api_main_router.include_router(tenants_router)
    api_main_router.include_router(tenant_documents_router)  # Includes /tenants/{tenant_id}/documents endpoints
    api_main_router.include_router(document_taxonomy_router)  # Includes /document-types/taxonomy endpoint
    api_main_router.include_router(units_router)
    api_main_router.include_router(reports_router)
    api_main_router.include_router(health_router)
    api_main_router.include_router(maintenance_router)
    api_main_router.include_router(quickbooks_router, prefix="/quickbooks", tags=["QuickBooks"])

    # Define comprehensive health check endpoints
    @api_main_router.get("/health")
    async def api_health_check():
        """Basic health check endpoint for load balancers and uptime monitoring"""
        logger.info("✅ Health check - API is healthy")
        return {
            "status": "ok",
            "message": "API is healthy",
            "timestamp": create_audit_datetime().isoformat()
        }
    
    @api_main_router.get("/health/detailed")
    async def detailed_health_check():
        """
        Comprehensive health check with database connectivity.
        Used for monitoring dashboards and alerting systems.
        """
        
        # Test database connectivity
        start_time = time.time()
        db_healthy = True
        db_error = None
        
        try:
            async with async_session() as session:
                await session.execute(text("SELECT 1"))
            response_time_ms = round((time.time() - start_time) * 1000, 2)
        except Exception as e:
            db_healthy = False
            db_error = str(e)
            response_time_ms = round((time.time() - start_time) * 1000, 2)
        
        # Compile overall health status
        overall_health = {
            "status": "healthy" if db_healthy else "unhealthy",
            "timestamp": create_audit_datetime().isoformat(),
            "services": {
                "api": {
                    "status": "healthy",
                    "message": "API service operational"
                },
                "database": {
                    "status": "healthy" if db_healthy else "unhealthy",
                    "response_time_ms": response_time_ms,
                    "pool_size": engine.pool.size(),
                    "checked_out": engine.pool.checkedout(),
                    "error": db_error
                }
            }
        }
        
        # Set appropriate HTTP status code if unhealthy
        if not db_healthy:
            from fastapi import Response
            return Response(
                content=json.dumps(overall_health),
                status_code=503,  # Service Unavailable
                media_type="application/json"
            )
        
        logger.info("✅ Detailed health check completed successfully")
        return overall_health

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
