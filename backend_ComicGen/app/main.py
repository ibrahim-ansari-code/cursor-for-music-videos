"""
FastAPI main application entry point.

MeloVue API - Converts audio to comic panel images using:
- ElevenLabs for transcription
- Claude for intelligent prompt generation (with vision support)
- Gemini for image generation
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import audio_routes
from app.api import pipeline_routes
from app.api import gemini_routes

app = FastAPI(
    title="MeloVue API",
    description="AI Music Video Generator API - Audio to Comic Panel Images",
    version="2.0.0"
)

# CORS middleware - allow all origins for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(audio_routes.router)
app.include_router(pipeline_routes.router)
app.include_router(gemini_routes.router)


@app.get("/")
async def root():
    """Root endpoint - API info and health check."""
    return {
        "message": "MeloVue API is running",
        "status": "ok",
        "version": "2.0.0",
        "endpoints": {
            "audio_generate": "/audio/generate-comic",
            "audio_transcribe": "/audio/transcribe",
            "pipeline": "/pipeline/run",
            "pipeline_health": "/pipeline/health",
            "gemini": "/gemini/generate-panel",
            "health": "/health"
        }
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}
