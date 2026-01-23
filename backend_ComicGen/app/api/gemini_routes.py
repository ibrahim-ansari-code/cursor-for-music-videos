"""
Gemini Image Generation API endpoints.

Provides HTTP endpoints for:
- Single panel/image generation
- Batch image generation
- Gemini service health check
"""

from typing import Optional, List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.gemini_service import gemini_service


router = APIRouter(prefix="/gemini", tags=["gemini"])


# ============================================================================
# Request/Response Models
# ============================================================================

class GeneratePanelRequest(BaseModel):
    """Request to generate a single panel image."""
    prompt: str = Field(..., description="Text prompt for image generation")
    panel_id: int = Field(default=1, description="Panel identifier")
    style: str = Field(default="storybook", description="Art style")
    negative_prompt: Optional[str] = Field(None, description="What to avoid")
    aspect_ratio: str = Field(default="16:9", description="Image aspect ratio")
    temperature: float = Field(default=0.2, ge=0.0, le=1.0)


class GeneratePanelResponse(BaseModel):
    """Response from panel generation."""
    success: bool
    panel_id: int
    image_base64: Optional[str] = None
    mime_type: str = "image/png"
    prompt_used: Optional[str] = None
    error_message: Optional[str] = None


class BatchGenerateRequest(BaseModel):
    """Request to generate multiple panel images."""
    prompts: List[dict] = Field(
        ..., 
        description="List of {prompt, panel_id, negative_prompt} dicts"
    )
    style: str = Field(default="storybook")
    aspect_ratio: str = Field(default="16:9")
    temperature: float = Field(default=0.2, ge=0.0, le=1.0)


class BatchGenerateResponse(BaseModel):
    """Response from batch generation."""
    success: bool
    total: int
    successful: int
    failed: int
    panels: List[dict] = Field(default_factory=list)
    error_message: Optional[str] = None


class GeminiHealthResponse(BaseModel):
    """Gemini health check response."""
    status: str
    configured: bool
    model: str
    message: str


# ============================================================================
# Endpoints
# ============================================================================

@router.post("/generate-panel", response_model=GeneratePanelResponse)
async def generate_panel(request: GeneratePanelRequest):
    """
    Generate a single comic panel image.
    
    Args:
        prompt: Text description of the scene
        panel_id: Identifier for this panel
        style: Art style (storybook, comic, manga, etc.)
        negative_prompt: What to avoid in the image
        aspect_ratio: Image dimensions (16:9, 1:1, 4:3)
        temperature: Generation randomness (0.2 recommended)
    
    Returns:
        Generated image as base64
    """
    if not gemini_service.is_configured():
        raise HTTPException(
            status_code=503,
            detail="Gemini API not configured. Set GEMINI_API_KEY or GOOGLE_API_KEY."
        )
    
    try:
        result = await gemini_service.generate_panel(
            prompt=request.prompt,
            panel_id=request.panel_id,
            style=request.style,
            negative_prompt=request.negative_prompt,
            aspect_ratio=request.aspect_ratio,
            temperature=request.temperature
        )
        
        return GeneratePanelResponse(
            success=result.success,
            panel_id=result.panel_id,
            image_base64=result.image_base64,
            mime_type=result.mime_type,
            prompt_used=result.prompt,
            error_message=result.error_message
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Image generation error: {str(e)}")


@router.post("/generate-batch", response_model=BatchGenerateResponse)
async def generate_batch(request: BatchGenerateRequest):
    """
    Generate multiple comic panel images.
    
    Args:
        prompts: List of prompt dictionaries with panel_id and prompt
        style: Art style for all panels
        aspect_ratio: Image dimensions for all panels
        temperature: Generation randomness
    
    Returns:
        List of generated images with success/failure status
    """
    if not gemini_service.is_configured():
        raise HTTPException(
            status_code=503,
            detail="Gemini API not configured. Set GEMINI_API_KEY or GOOGLE_API_KEY."
        )
    
    try:
        results = await gemini_service.generate_batch(
            prompts=request.prompts,
            style=request.style,
            aspect_ratio=request.aspect_ratio,
            temperature=request.temperature
        )
        
        panels = []
        successful = 0
        failed = 0
        
        for result in results:
            if result.success:
                successful += 1
            else:
                failed += 1
            
            panels.append({
                "panel_id": result.panel_id,
                "success": result.success,
                "image_base64": result.image_base64,
                "mime_type": result.mime_type,
                "prompt": result.prompt,
                "error_message": result.error_message
            })
        
        return BatchGenerateResponse(
            success=failed == 0,
            total=len(panels),
            successful=successful,
            failed=failed,
            panels=panels
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Batch generation error: {str(e)}")


@router.get("/health", response_model=GeminiHealthResponse)
async def gemini_health():
    """
    Health check for Gemini service.
    """
    configured = gemini_service.is_configured()
    
    return GeminiHealthResponse(
        status="ok" if configured else "not_configured",
        configured=configured,
        model=gemini_service.model,
        message="Gemini ready" if configured else "GEMINI_API_KEY not set"
    )
