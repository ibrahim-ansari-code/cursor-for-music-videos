"""
Pydantic models for Claude prompt generation service.

These models are used with Claude's Tool Use (Function Calling) feature
to ensure structured, type-safe output for comic panel generation.
"""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field


# ============================================================================
# Character Models
# ============================================================================

class CharacterVisual(BaseModel):
    """Fixed visual description for a character."""
    name: str = Field(..., description="Character name")
    description: str = Field(
        ..., 
        description="Detailed visual description that will be reused in all panels"
    )


# ============================================================================
# Panel Models
# ============================================================================

class PanelPromptInternal(BaseModel):
    """
    Internal panel prompt structure from Claude.
    
    This is what Claude outputs via Tool Use, before post-processing.
    Contains characters_present list for programmatic injection.
    """
    panel_id: int = Field(..., description="Sequential panel number (1-indexed)")
    characters_present: List[str] = Field(
        ..., 
        description="List of character names appearing in this panel (even if narrative uses pronouns)"
    )
    scene_description: str = Field(
        ..., 
        description="Natural English scene description (can use pronouns)"
    )
    negative_prompt: Optional[str] = Field(
        None, 
        description="What to avoid in the image"
    )
    mood: Optional[str] = Field(
        None, 
        description="Emotional tone of the panel"
    )
    camera_angle: Optional[str] = Field(
        None, 
        description="Camera perspective (e.g., 'close-up', 'wide shot')"
    )
    start_s: Optional[float] = Field(
        None, 
        description="Start time in audio (seconds)"
    )
    end_s: Optional[float] = Field(
        None, 
        description="End time in audio (seconds)"
    )


class PanelPrompt(BaseModel):
    """
    Final panel prompt after post-processing.
    
    Contains the fully constructed prompt with character descriptions injected.
    """
    panel_id: int = Field(..., description="Sequential panel number")
    prompt: str = Field(
        ..., 
        description="Natural English prompt for Gemini, includes character descriptions"
    )
    negative_prompt: Optional[str] = Field(
        None, 
        description="What to avoid in image"
    )
    mood: Optional[str] = Field(
        None, 
        description="Emotional tone of the panel"
    )
    camera_angle: Optional[str] = Field(
        None, 
        description="Camera perspective"
    )
    start_s: Optional[float] = Field(
        None, 
        description="Start time in audio"
    )
    end_s: Optional[float] = Field(
        None, 
        description="End time in audio"
    )


# ============================================================================
# Response Models (Tool Use Schema)
# ============================================================================

class ComicGenerationInternalResponse(BaseModel):
    """
    Internal response from Claude Tool Use.
    
    This is the schema Claude outputs before post-processing.
    Contains character sheet and panels with characters_present list.
    """
    characters: Dict[str, str] = Field(
        ..., 
        description="Character name -> fixed visual description mapping"
    )
    global_style: str = Field(
        ..., 
        description="Overall artistic style for all panels"
    )
    global_mood: str = Field(
        ..., 
        description="Overall emotional tone"
    )
    panels: List[PanelPromptInternal] = Field(
        ..., 
        description="List of panel prompts with character tracking"
    )


class ComicGenerationResponse(BaseModel):
    """
    Final response after post-processing.
    
    Contains fully constructed prompts ready for Gemini.
    """
    characters: Dict[str, str] = Field(
        ..., 
        description="Character name -> fixed visual description"
    )
    global_style: str = Field(
        ..., 
        description="Overall artistic style"
    )
    global_mood: str = Field(
        ..., 
        description="Overall emotional tone"
    )
    panels: List[PanelPrompt] = Field(
        ..., 
        description="List of final panel prompts ready for image generation"
    )


class StyleAnalysisResponse(BaseModel):
    """Response from style reference image analysis."""
    style_keywords: str = Field(
        ..., 
        description="Comma-separated prompt-engineering keywords for Gemini"
    )
    medium: Optional[str] = Field(
        None, 
        description="Art medium (e.g., 'watercolor', 'digital painting')"
    )
    lighting: Optional[str] = Field(
        None, 
        description="Lighting style (e.g., 'soft ambient', 'dramatic')"
    )
    color_palette: Optional[str] = Field(
        None, 
        description="Color palette description"
    )


class CharacterSheetResponse(BaseModel):
    """Response from character sheet extraction."""
    characters: Dict[str, str] = Field(
        ..., 
        description="Character name -> fixed visual description"
    )
