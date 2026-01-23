"""
Pipeline API endpoints.

Provides HTTP endpoints for:
- Running the full audio-to-comic pipeline
- Generating prompts only (for testing)
- Health checks for pipeline services
"""

import base64
from pathlib import Path
from typing import Optional, List
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel, Field

from app.services.pipeline import pipeline_orchestrator, PipelineConfig, PipelineResult
from app.services.claude_prompt_service import claude_prompt_service
from app.services.gemini_service import gemini_service


router = APIRouter(prefix="/pipeline", tags=["pipeline"])


# ============================================================================
# Request/Response Models
# ============================================================================

class PipelineRequest(BaseModel):
    """Request to run the pipeline from a transcript."""
    comic_script: List[dict] = Field(..., description="List of transcript segments")
    style: str = Field(default="storybook", description="Art style for images")
    aspect_ratio: str = Field(default="16:9", description="Image aspect ratio")
    style_reference_image_base64: Optional[str] = Field(
        None, 
        description="Base64-encoded style reference image"
    )
    prompt_temperature: float = Field(
        default=0.3, 
        ge=0.0, 
        le=1.0,
        description="Temperature for prompt generation (0.3 recommended)"
    )


class PipelineResponse(BaseModel):
    """Response from pipeline execution."""
    success: bool
    total_panels: int = 0
    total_pages: int = 0
    successful_images: int = 0
    failed_images: int = 0
    successful_pages: int = 0
    failed_pages: int = 0
    pages: List[dict] = Field(default_factory=list, description="Comic pages (each page = one image with multiple panels)")
    panels: List[dict] = Field(default_factory=list, description="Backward compatibility - flattened panel list")
    execution_time_s: float = 0.0
    error_message: Optional[str] = None


class PromptGenerationRequest(BaseModel):
    """Request to generate prompts only (no images)."""
    comic_script: List[dict] = Field(..., description="List of transcript segments")
    style_reference_image_base64: Optional[str] = Field(
        None, 
        description="Base64-encoded style reference image"
    )
    temperature: float = Field(default=0.3, ge=0.0, le=1.0)


class PromptGenerationResponse(BaseModel):
    """Response from prompt generation."""
    success: bool
    characters: dict = Field(default_factory=dict)
    global_style: str = ""
    global_mood: str = ""
    panels: List[dict] = Field(default_factory=list)
    style_keywords: Optional[str] = None
    error_message: Optional[str] = None


class HealthResponse(BaseModel):
    """Pipeline health check response."""
    status: str
    claude_configured: bool
    gemini_configured: bool
    message: str


# ============================================================================
# Endpoints
# ============================================================================

@router.post("/run", response_model=PipelineResponse)
async def run_pipeline(request: PipelineRequest):
    """
    Run the full pipeline from transcript to images.
    
    Steps:
    1. Generate prompts using Claude (with optional style reference)
    2. Generate images using Gemini
    
    Returns:
        Generated comic panels with base64-encoded images
    """
    try:
        # Decode style reference image if provided
        style_ref_bytes = None
        if request.style_reference_image_base64:
            try:
                style_ref_bytes = base64.b64decode(request.style_reference_image_base64)
            except Exception:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid base64 encoding for style reference image"
                )
        
        # Configure pipeline
        config = PipelineConfig(
            output_dir=Path("/tmp/pipeline_output"),
            image_style=request.style,
            aspect_ratio=request.aspect_ratio,
            save_images=False,  # Return base64 instead
            save_metadata=False,
            style_reference_image=style_ref_bytes,
            prompt_temperature=request.prompt_temperature
        )
        
        # Run pipeline
        result = await pipeline_orchestrator.run_from_transcript(
            comic_script=request.comic_script,
            config=config
        )
        
        return PipelineResponse(
            success=result.success,
            total_panels=result.total_panels,
            total_pages=result.total_pages,
            successful_images=result.successful_images,
            failed_images=result.failed_images,
            successful_pages=result.successful_pages,
            failed_pages=result.failed_pages,
            pages=result.pages,
            panels=result.panels,  # Backward compatibility
            execution_time_s=result.execution_time_s,
            error_message=result.error_message
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pipeline error: {str(e)}")


@router.post("/generate-prompts", response_model=PromptGenerationResponse)
async def generate_prompts(request: PromptGenerationRequest):
    """
    Generate prompts only (no image generation).
    
    Useful for:
    - Testing prompt quality
    - Inspecting prompts before image generation
    - Debugging character consistency
    
    Returns:
        Generated prompts with character sheet and style keywords
    """
    try:
        # Decode style reference image if provided
        style_ref_bytes = None
        if request.style_reference_image_base64:
            try:
                style_ref_bytes = base64.b64decode(request.style_reference_image_base64)
            except Exception:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid base64 encoding for style reference image"
                )
        
        # Generate prompts
        result = await pipeline_orchestrator.generate_prompts_only(
            comic_script=request.comic_script,
            style_reference_image=style_ref_bytes,
            temperature=request.temperature
        )
        
        if not result.success or not result.response:
            return PromptGenerationResponse(
                success=False,
                error_message=result.error_message
            )
        
        # Format panels for response
        panels = []
        for panel in result.response.panels:
            panels.append({
                "panel_id": panel.panel_id,
                "prompt": panel.prompt,
                "negative_prompt": panel.negative_prompt,
                "mood": panel.mood,
                "camera_angle": panel.camera_angle,
                "start_s": panel.start_s,
                "end_s": panel.end_s
            })
        
        return PromptGenerationResponse(
            success=True,
            characters=result.response.characters,
            global_style=result.response.global_style,
            global_mood=result.response.global_mood,
            panels=panels,
            style_keywords=result.style_keywords
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prompt generation error: {str(e)}")


@router.get("/health", response_model=HealthResponse)
async def pipeline_health():
    """
    Health check for pipeline services.
    
    Checks:
    - Claude API configuration
    - Gemini API configuration
    """
    claude_ok = claude_prompt_service.is_configured()
    gemini_ok = gemini_service.is_configured()
    
    all_ok = claude_ok and gemini_ok
    
    messages = []
    if not claude_ok:
        messages.append("Claude not configured (ANTHROPIC_API_KEY)")
    if not gemini_ok:
        messages.append("Gemini not configured (GEMINI_API_KEY)")
    
    return HealthResponse(
        status="ok" if all_ok else "degraded",
        claude_configured=claude_ok,
        gemini_configured=gemini_ok,
        message="All services ready" if all_ok else "; ".join(messages)
    )
