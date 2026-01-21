"""
Gemini Image Generation Service.

Uses Google's Gemini API to generate images from text prompts.
Supports the gemini-2.5-flash-image model for high-quality image generation.
"""

import base64
import asyncio
import io
from pathlib import Path
from typing import Optional
from dataclasses import dataclass
from functools import lru_cache

from pydantic_settings import BaseSettings


# ============================================================================
# Configuration
# ============================================================================

def _find_env_file() -> str:
    """Find .env file in current or parent directories."""
    current = Path.cwd()
    for directory in [current, current.parent, current.parent.parent]:
        env_path = directory / ".env"
        if env_path.exists():
            return str(env_path)
    return ".env"


class GeminiSettings(BaseSettings):
    """Gemini API settings loaded from environment variables."""
    
    gemini_api_key: str | None = None
    google_api_key: str | None = None  # Alternative env var name
    
    model_config = {
        "env_file": _find_env_file(),
        "env_file_encoding": "utf-8",
        "extra": "ignore"
    }
    
    def get_api_key(self) -> str | None:
        """Get API key from either GEMINI_API_KEY or GOOGLE_API_KEY."""
        return self.gemini_api_key or self.google_api_key


@lru_cache()
def get_gemini_settings() -> GeminiSettings:
    """Get cached Gemini settings instance."""
    return GeminiSettings()


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class ImageResult:
    """Result of image generation."""
    success: bool
    image_base64: Optional[str] = None
    mime_type: str = "image/png"
    error_message: Optional[str] = None
    prompt_used: Optional[str] = None


@dataclass
class PanelResult:
    """Result of panel image generation."""
    panel_id: int
    success: bool
    image_base64: Optional[str] = None
    mime_type: str = "image/png"
    error_message: Optional[str] = None
    prompt: Optional[str] = None
    file_path: Optional[str] = None


# ============================================================================
# Gemini Service
# ============================================================================

class GeminiService:
    """Service for generating images using Google's Gemini API."""
    
    def __init__(self):
        self.settings = get_gemini_settings()
        self.model = "gemini-2.0-flash-exp"  # Gemini 2.0 with native image generation
        self._client = None
    
    def is_configured(self) -> bool:
        """Check if the Gemini API is configured."""
        return self.settings.get_api_key() is not None
    
    def _get_client(self):
        """Get or create the Gemini client."""
        if self._client is None:
            try:
                from google import genai
                api_key = self.settings.get_api_key()
                if not api_key:
                    raise ValueError("GEMINI_API_KEY or GOOGLE_API_KEY not configured")
                self._client = genai.Client(api_key=api_key)
            except ImportError:
                raise ImportError(
                    "google-genai package not installed. "
                    "Run: pip install google-genai"
                )
        return self._client
    


    
    async def generate_panel(
        self,
        prompt: str,
        panel_id: int,
        style: str = "storybook",
        negative_prompt: Optional[str] = None,
        aspect_ratio: str = "16:9",
        num_panels: int = 4,
        temperature: float = 0.2
    ) -> PanelResult:
        """
        Generate a comic page with multiple panels.
        
        Args:
            prompt: The prompt for the panel/scene
            panel_id: Unique identifier for this comic page
            style: Art style (storybook, comic, manga, etc.)
            negative_prompt: What to avoid (will be added to prompt)
            aspect_ratio: Image aspect ratio
            num_panels: Number of panels to include in the comic page (default: 4)
            temperature: Generation temperature (lower = more deterministic, default: 0.2)
        
        Returns:
            PanelResult with the generated comic page image
        """
        # Build style-enhanced prompt optimized for comics
        style_prompts = {
            "storybook": "children's storybook comic illustration style, warm colors, expressive characters, whimsical details",
            "comic": "classic American comic book art style, bold ink lines, dynamic poses, vibrant colors, halftone dots",
            "manga": "Japanese manga art style, expressive eyes, speed lines, screentones, dramatic angles",
            "watercolor": "watercolor comic style, soft washes, painterly panels, dreamy atmosphere",
            "digital_art": "modern digital comic art style, clean linework, cel shading, polished finish",
            "realistic": "realistic graphic novel style, detailed rendering, cinematic lighting, painterly textures"
        }
        
        style_prefix = style_prompts.get(style.lower(), style_prompts["comic"])
        
        # Add negative prompt guidance if provided
        enhanced_prompt = prompt
        if negative_prompt:
            enhanced_prompt = f"{prompt}\n\nAVOID: {negative_prompt}"
        
        result = await self.generate_image(
            prompt=enhanced_prompt,
            aspect_ratio=aspect_ratio,
            style_prefix=style_prefix,
            num_panels=num_panels,
            temperature=temperature
        )
        
        return PanelResult(
            panel_id=panel_id,
            success=result.success,
            image_base64=result.image_base64,
            mime_type=result.mime_type,
            error_message=result.error_message,
            prompt=result.prompt_used
        )
    
    async def generate_batch(
        self,
        prompts: list[dict],
        style: str = "comic",
        aspect_ratio: str = "16:9",
        delay_between: float = 1.0,
        num_panels: int = 4,
        temperature: float = 0.2
    ) -> list[PanelResult]:
        """
        Generate multiple comic page images in batch.
        
        Args:
            prompts: List of dicts with 'prompt' and 'panel_id' keys
            style: Art style for all pages (default: comic)
            aspect_ratio: Aspect ratio for all pages
            delay_between: Delay between requests to avoid rate limiting
            num_panels: Number of panels per comic page (default: 4)
            temperature: Generation temperature (lower = more deterministic, default: 0.2)
        
        Returns:
            List of PanelResult objects (each containing a multi-panel comic page)
        """
        results = []
        
        for i, panel_data in enumerate(prompts):
            prompt = panel_data.get("prompt", "")
            panel_id = panel_data.get("panel_id", i + 1)
            negative_prompt = panel_data.get("negative_prompt")
            
            result = await self.generate_panel(
                prompt=prompt,
                panel_id=panel_id,
                style=style,
                negative_prompt=negative_prompt,
                aspect_ratio=aspect_ratio,
                num_panels=num_panels,
                temperature=temperature
            )
            results.append(result)
            
            # Add delay between requests to avoid rate limiting
            if i < len(prompts) - 1 and delay_between > 0:
                await asyncio.sleep(delay_between)
        
        return results
    
    def save_image(
        self,
        image_base64: str,
        output_path: Path,
        mime_type: str = "image/png"
    ) -> Path:
        """
        Save a base64-encoded image to disk.
        
        Args:
            image_base64: Base64-encoded image data
            output_path: Path to save the image
            mime_type: MIME type of the image
        
        Returns:
            Path to the saved image
        """
        # Ensure parent directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Decode and save
        image_data = base64.b64decode(image_base64)
        
        with open(output_path, "wb") as f:
            f.write(image_data)
        
        return output_path


# Global service instance
gemini_service = GeminiService()
