import logging

from fastapi import APIRouter, FastAPI, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.datastructures import FormData

# Configure logging
logging.basicConfig(level=logging.INFO)
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
        "http://127.0.0.1:5173",
        "https://127.0.0.1:5173",
        "https://app.brikli.com",
        "https://brikli.azurewebsites.net",
        "https://lemon-island-038ac790f.6.azurestaticapps.net",
        "https://icy-glacier-00294140f.6.azurestaticapps.net",
        "https://brikli-staging.azurewebsites.net",
        "https://thankful-pond-068620f0f.6.azurestaticapps.net",
        "https://brikli-api-8919-151e4fdf-aa5gqdc5.onporter.run"
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
        "brikli.azurewebsites.net",
        "localhost",
        "brikli-staging.azurewebsites.net",
        "icy-glacier-00294140f.6.azurestaticapps.net",
        "thankful-pond-068620f0f.6.azurestaticapps.net",
        "*.onporter.run",  # Allow all Porter preview environments
    ]
)

# Add the RequestValidationError handler here


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    body_representation = exc.body  # Default to original body

    if isinstance(exc.body, FormData):
        # If body is FormData, create a serializable representation
        form_fields = {}
        file_fields = {}
        try:
            for key, value in exc.body.items():
                if isinstance(value, UploadFile):
                    file_fields[key] = value.filename if value.filename is not None else "[FileUploadWithoutName]"
                elif isinstance(value, str):  # Standard form fields
                    form_fields[key] = value
                else:  # Other types, convert to string to be safe
                    form_fields[key] = str(value)

            if form_fields or file_fields:
                body_representation = {
                    "form_fields": form_fields, "file_fields": file_fields}
            else:
                body_representation = "[Empty FormData Content]"
        except (TypeError, AttributeError, ValueError) as e:  # Catch more specific errors
            logger.exception(
                "Error processing FormData in exception handler:"
            )
            body_representation = "[FormData Content - Error during processing]"

    # For logging, use a potentially more verbose but safe string representation of the original body
    log_body_str = str(exc.body)
    if isinstance(exc.body, FormData):
        # Avoid logging full file content
        log_body_str = f"[FormData with keys: {list(exc.body.keys())}]"

    logger.error(
        "Validation error: %s for request: %s with body: %s", exc.errors(), request.url, log_body_str
    )

    # Ensure the final body for the JSON response is serializable
    final_response_body = body_representation
    if not isinstance(body_representation, (dict, list, str, int, float, bool, type(None))):
        final_response_body = str(body_representation)

    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors(), "body": final_response_body},
    )

# Router import + error trapping
try:
    # Router Imports
    from Backend.api.accounting import accounting_api_router
    from Backend.api.ai import router as ai_router
    from Backend.api.auth import router as auth_router
    from Backend.api.dashboard import router as dashboard_router
    from Backend.api.health import router as health_router
    from Backend.api.leases import router as leases_router
    from Backend.api.properties import router as properties_router
    from Backend.api.rent_tracker import router as rent_tracker_router
    from Backend.api.reports import router as reports_router
    from Backend.api.tenants import router as tenants_router
    from Backend.api.units import router as units_router
    from Backend.api.maintenance import router as maintenance_router

    # Include routers into the central api_main_router
    # Their internal prefixes (e.g., /auth, /properties) will apply
    api_main_router.include_router(auth_router)
    api_main_router.include_router(properties_router)
    api_main_router.include_router(dashboard_router)
    api_main_router.include_router(leases_router)
    # Include the new accounting router with its own base prefix
    api_main_router.include_router(accounting_api_router, prefix="/accounting")
    api_main_router.include_router(ai_router)
    api_main_router.include_router(tenants_router)
    api_main_router.include_router(rent_tracker_router)
    api_main_router.include_router(units_router)
    api_main_router.include_router(reports_router)
    api_main_router.include_router(health_router)
    api_main_router.include_router(maintenance_router)

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


# Initialize all models before creating the FastAPI app

logger.info("🚀 FastAPI app initialization complete.")
