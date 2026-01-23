"""
API endpoints for audio file processing.

Provides HTTP endpoints for:
- Audio file upload and transcription
- Full pipeline from audio to comic panels
"""

import json
import tempfile
import asyncio
from pathlib import Path
from typing import Optional, List
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

import sys
backend_dir = Path(__file__).parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from transcription import TranscriptionService
from app.services.pipeline import pipeline_orchestrator, PipelineConfig, PipelineResult


router = APIRouter(prefix="/audio", tags=["audio"])


# ============================================================================
# Request/Response Models
# ============================================================================

class TranscriptionResponse(BaseModel):
    """Response from audio transcription."""
    success: bool
    transcript: List[dict] = Field(default_factory=list)
    metadata: Optional[dict] = None
    error_message: Optional[str] = None


class AudioPipelineResponse(BaseModel):
    """Response from full audio pipeline."""
    success: bool
    total_panels: int = 0
    successful_images: int = 0
    failed_images: int = 0
    panels: List[dict] = Field(default_factory=list)
    transcript: List[dict] = Field(default_factory=list)
    gumloop_run_id: Optional[str] = None
    execution_time_s: float = 0.0
    error_message: Optional[str] = None


class PipelineStatusResponse(BaseModel):
    """Response for pipeline status check."""
    job_id: str
    status: str  # pending, transcribing, generating_prompts, generating_images, complete, error
    progress: float = 0.0
    message: str = ""
    result: Optional[AudioPipelineResponse] = None


# Store for async job tracking
_job_store: dict = {}


# ============================================================================
# Endpoints
# ============================================================================

@router.post("/transcribe", response_model=TranscriptionResponse)
async def transcribe_audio(
    file: UploadFile = File(...),
    language: Optional[str] = Form(None),
    keyterms: Optional[str] = Form(None)
):
    """
    Transcribe an audio file to comic script format.
    
    Args:
        file: Audio file (MP3, WAV, M4A)
        language: Optional language code (e.g., 'eng', 'en')
        keyterms: Optional comma-separated list of character names/terms
    
    Returns:
        Transcribed comic script segments
    """
    # Validate file type
    allowed_types = ['audio/mpeg', 'audio/mp3', 'audio/wav', 'audio/x-wav', 'audio/m4a', 'audio/mp4']
    if file.content_type not in allowed_types and not file.filename.endswith(('.mp3', '.wav', '.m4a')):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type: {file.content_type}. Supported: MP3, WAV, M4A"
        )
    
    try:
        # Save uploaded file to temp location
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.filename).suffix) as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = Path(tmp.name)
        
        try:
            # Initialize transcription service
            service = TranscriptionService()
            
            # Parse keyterms
            keyterms_list = None
            if keyterms:
                keyterms_list = [k.strip() for k in keyterms.split(",") if k.strip()]
            
            # Transcribe
            result = service.transcribe_audio(
                audio_path=tmp_path,
                language=language,
                keyterms=keyterms_list
            )
            
            # Format as comic script
            comic_script = service.format_comic_script(result, file.filename)
            
            # Convert to array format
            output_array = []
            if comic_script.get("metadata"):
                output_array.append({
                    "_type": "metadata",
                    **comic_script["metadata"]
                })
            if comic_script.get("full_transcript"):
                output_array.append({
                    "_type": "full_transcript",
                    "text": comic_script["full_transcript"]
                })
            output_array.extend(comic_script.get("segments", []))
            
            return TranscriptionResponse(
                success=True,
                transcript=output_array,
                metadata=comic_script.get("metadata")
            )
            
        finally:
            # Clean up temp file
            tmp_path.unlink(missing_ok=True)
            
    except ValueError as e:
        raise HTTPException(status_code=500, detail=f"Transcription service error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")


@router.post("/generate-comic", response_model=AudioPipelineResponse)
async def generate_comic_from_audio(
    file: UploadFile = File(...),
    style: str = Form("storybook"),
    aspect_ratio: str = Form("16:9"),
    language: Optional[str] = Form(None),
    keyterms: Optional[str] = Form(None)
):
    """
    Full pipeline: Upload audio file → Transcribe → Generate comic panels.
    
    This endpoint handles the complete flow:
    1. Transcribe audio to comic script
    2. Send to Gumloop for prompt generation
    3. Generate images with Gemini
    
    Args:
        file: Audio file (MP3, WAV, M4A)
        style: Art style for images (default: storybook)
        aspect_ratio: Aspect ratio for images (default: 16:9)
        language: Optional language code for transcription
        keyterms: Optional comma-separated list of character names/terms
    
    Returns:
        Generated comic panels with images as base64
    """
    # Validate file type
    allowed_types = ['audio/mpeg', 'audio/mp3', 'audio/wav', 'audio/x-wav', 'audio/m4a', 'audio/mp4']
    if file.content_type not in allowed_types and not file.filename.endswith(('.mp3', '.wav', '.m4a')):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type: {file.content_type}. Supported: MP3, WAV, M4A"
        )
    
    try:
        # Save uploaded file to temp location
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.filename).suffix) as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = Path(tmp.name)
        
        try:
            # Step 1: Transcribe audio
            service = TranscriptionService()
            
            keyterms_list = None
            if keyterms:
                keyterms_list = [k.strip() for k in keyterms.split(",") if k.strip()]
            
            result = service.transcribe_audio(
                audio_path=tmp_path,
                language=language,
                keyterms=keyterms_list
            )
            
            comic_script_dict = service.format_comic_script(result, file.filename)
            
            # Convert to array format
            transcript = []
            if comic_script_dict.get("metadata"):
                transcript.append({
                    "_type": "metadata",
                    **comic_script_dict["metadata"]
                })
            if comic_script_dict.get("full_transcript"):
                transcript.append({
                    "_type": "full_transcript",
                    "text": comic_script_dict["full_transcript"]
                })
            transcript.extend(comic_script_dict.get("segments", []))
            
            # Step 2: Run pipeline with transcript
            config = PipelineConfig(
                output_dir=Path("/tmp/pipeline_output"),
                image_style=style,
                aspect_ratio=aspect_ratio,
                save_images=False,  # Return base64 instead
                save_metadata=False
            )
            
            pipeline_result = await pipeline_orchestrator.run_from_transcript(
                comic_script=transcript,
                config=config
            )
            
            return AudioPipelineResponse(
                success=pipeline_result.success,
                total_panels=pipeline_result.total_panels,
                successful_images=pipeline_result.successful_images,
                failed_images=pipeline_result.failed_images,
                panels=pipeline_result.panels,
                transcript=transcript,
                gumloop_run_id=pipeline_result.gumloop_run_id,
                execution_time_s=pipeline_result.execution_time_s,
                error_message=pipeline_result.error_message
            )
            
        finally:
            # Clean up temp file
            tmp_path.unlink(missing_ok=True)
            
    except ValueError as e:
        raise HTTPException(status_code=500, detail=f"Service configuration error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pipeline failed: {str(e)}")


@router.get("/health")
async def audio_health():
    """
    Health check for audio processing services.
    """
    try:
        service = TranscriptionService()
        transcription_ok = True
    except Exception as e:
        transcription_ok = False
    
    return {
        "status": "ok" if transcription_ok else "degraded",
        "transcription_configured": transcription_ok,
        "message": "Audio processing ready" if transcription_ok else "Transcription service not configured"
    }
