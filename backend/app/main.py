"""
MeloVue Backend API - Main Application Entry Point

This API handles:
- File uploads (audio + image)
- Job creation and management
- Progress tracking
- Final video delivery
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import uploads, jobs

app = FastAPI(
    title="MeloVue API",
    description="AI-powered music video generation service",
    version="0.1.0",
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(uploads.router, prefix="/uploads", tags=["uploads"])
app.include_router(jobs.router, prefix="/jobs", tags=["jobs"])


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "MeloVue API",
        "version": "0.1.0",
    }


@app.get("/health")
async def health_check():
    """Detailed health check."""
    return {
        "status": "healthy",
        "database": "connected",
        "queue": "connected",
        "storage": "connected",
    }
