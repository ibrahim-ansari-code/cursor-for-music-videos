"""
FastAPI main application entry point.
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from app.api import gumloop
from app.api import gemini_routes
from app.api import pipeline_routes
from app.api import audio_routes
from app.models.gumloop import GumloopRequest, GumloopResponse
import json

app = FastAPI(
    title="MeloVue API",
    description="AI Music Video Generator API - Audio to Comic Panel Images",
    version="1.0.0"
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
app.include_router(gumloop.router)
app.include_router(gemini_routes.router)
app.include_router(pipeline_routes.router)
app.include_router(audio_routes.router)


@app.get("/")
async def root():
    """Root endpoint - health check."""
    return {
        "message": "MeloVue API is running",
        "status": "ok",
        "version": "1.0.0",
        "endpoints": {
            "audio_generate": "/audio/generate-comic",
            "audio_transcribe": "/audio/transcribe",
            "pipeline": "/pipeline/run",
            "pipeline_images": "/pipeline/generate-images",
            "pipeline_gumloop": "/pipeline/process-gumloop",
            "gemini": "/gemini/generate-panel",
            "gumloop": "/gumloop/process-transcript",
            "health": "/health"
        }
    }


@app.post("/")
async def root_post(request: Request):
    """
    Root POST endpoint - forwards to Gumloop process-transcript endpoint.
    
    This allows Gumloop workflows to POST to the root URL without needing
    to specify the full endpoint path.
    
    Accepts both structured GumloopRequest JSON and raw text/other formats.
    """
    try:
        body = await request.json()
        
        # Try to parse as GumloopRequest
        if isinstance(body, dict):
            # If it has 'transcript' field, use it directly
            if "transcript" in body:
                gumloop_request = GumloopRequest(**body)
            # If it's a string response from Panel Prompt Generator, wrap it
            elif "response" in body or "text" in body or "prompt" in body:
                transcript = body.get("response") or body.get("text") or body.get("prompt") or str(body)
                gumloop_request = GumloopRequest(transcript=str(transcript))
            # Otherwise, try to convert the whole body to a transcript string
            else:
                gumloop_request = GumloopRequest(transcript=json.dumps(body))
        else:
            # If body is a string, wrap it
            gumloop_request = GumloopRequest(transcript=str(body))
        
        return await gumloop.process_transcript(gumloop_request)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error processing request: {str(e)}")


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}
