"""
Claude Prompt Generation Service.

Implements a three-pass architecture for generating comic panel prompts:
1. Style Reference Analysis (optional) - Extract prompt-engineering keywords from reference image
2. Character Sheet Extraction - Create consistent character descriptions
3. Panel Prompt Generation - Generate prompts with character descriptions injected

Uses Claude's Tool Use (Function Calling) for guaranteed structured output.
"""

import base64
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from functools import lru_cache
from dataclasses import dataclass

from pydantic_settings import BaseSettings

try:
    import anthropic
except ImportError:
    anthropic = None

from app.models.claude_schemas import (
    PanelPrompt,
    PanelPromptInternal,
    ComicGenerationResponse,
    ComicGenerationInternalResponse,
    StyleAnalysisResponse,
    CharacterSheetResponse
)


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


class ClaudeSettings(BaseSettings):
    """Claude API settings loaded from environment variables."""
    
    anthropic_api_key: Optional[str] = None
    claude_model: str = "claude-sonnet-4-20250514"
    claude_max_tokens: int = 16384  # Increased from 4096 to handle more panels
    
    model_config = {
        "env_file": _find_env_file(),
        "env_file_encoding": "utf-8",
        "extra": "ignore"
    }


@lru_cache()
def get_claude_settings() -> ClaudeSettings:
    """Get cached Claude settings instance."""
    return ClaudeSettings()


# ============================================================================
# System Prompts
# ============================================================================

STYLE_ANALYSIS_PROMPT = """
Analyze this reference image for style consistency.

Your task: Reverse-engineer the PROMPT KEYWORDS needed to replicate this visual style in an image generator.

Output a comma-separated list of artistic keywords describing:
1. Medium/technique (e.g., "watercolor", "3D render", "digital painting", "ink illustration")
2. Lighting style (e.g., "volumetric lighting", "cinematic", "soft ambient", "dramatic shadows")
3. Color palette (e.g., "neon-noir", "pastel", "muted earth tones", "high contrast")
4. Artistic style (e.g., "anime", "realistic", "stylized", "impressionist")
5. Composition elements (e.g., "wide angle", "close-up", "rule of thirds")

Example output: "watercolor illustration, soft ambient lighting, pastel color palette, stylized character design, wide angle composition"

DO NOT describe what you see in the image. Describe HOW to recreate the visual style.
Output ONLY the comma-separated keywords, nothing else.
"""

CHARACTER_SHEET_PROMPT = """
Analyze this comic script and extract ALL characters with their fixed visual descriptions.

For each character that appears, create a CONSISTENT visual description that will be used in EVERY panel where they appear.

Include:
- Physical appearance (hair color/style, facial features, body type)
- Clothing and accessories
- Distinctive features (glasses, scars, tattoos, etc.)
- Age/apparent age
- Posture/demeanor if relevant

IMPORTANT: These descriptions will be injected into EVERY panel prompt to ensure visual consistency.
Make them detailed enough for an image generator but concise (1-2 sentences).

Example output:
{
  "Alice": "Young woman in her 20s, shoulder-length blonde hair, wearing a blue business suit, confident posture, green eyes, small silver earrings",
  "Bob": "Middle-aged man with short gray beard, wearing red flannel shirt, portly build, kind expression, wire-rimmed glasses"
}
"""

PANEL_GENERATION_PROMPT = """
You are a professional comic book scripter writing prompts for Google Imagen (Gemini image generation).

CRITICAL STRUCTURE - YOU MUST FOLLOW THIS FORMAT:

For each panel, you MUST provide:
1. characters_present: List of character names that appear in this scene (even if narrative uses pronouns)
2. scene_description: Natural English description (can use pronouns like "she", "he", "they")
3. mood: Emotional tone of the panel
4. camera_angle: Perspective (e.g., "medium shot", "close-up", "wide establishing shot")

The final prompt will be constructed programmatically as:
"[Character descriptions] [Scene description] [Style keywords]"

EXAMPLE:
Panel scene from script: "She walks into the room and sits down, looking exhausted."

Your output:
- characters_present: ["Alice"]
- scene_description: "She walks into a dimly lit office and collapses into a leather chair, rubbing her temples with exhaustion."
- mood: "tired, stressed"
- camera_angle: "medium shot"

CRITICAL RULES:
1. ALWAYS list characters_present even if scene_description uses pronouns
2. scene_description can use natural pronouns - character descriptions will be injected programmatically
3. Write scene_description in NATURAL ENGLISH SENTENCES, NOT tag soup
4. Avoid generic tags like "4k, trending, artstation" - write descriptive prose
5. Make scenes visually interesting and dynamic
6. Ensure each panel tells part of the story clearly

Character Sheet:
{character_sheet}

Style Keywords (will be appended to all prompts):
{style_keywords}

Generate panel prompts that maintain character consistency and visual storytelling.
"""


# ============================================================================
# Service Class
# ============================================================================

@dataclass
class ClaudeResult:
    """Result from Claude prompt generation."""
    success: bool
    response: Optional[ComicGenerationResponse] = None
    error_message: Optional[str] = None
    style_keywords: Optional[str] = None
    character_sheet: Optional[Dict[str, str]] = None


class ClaudePromptService:
    """
    Service for generating comic panel prompts using Claude API.
    
    Implements a three-pass architecture:
    1. Style analysis (if reference image provided)
    2. Character sheet extraction
    3. Panel prompt generation with Tool Use
    """
    
    def __init__(self):
        self.settings = get_claude_settings()
        self._client = None
        self.logger = logging.getLogger(__name__)
    
    def is_configured(self) -> bool:
        """Check if the Claude API is configured."""
        return self.settings.anthropic_api_key is not None
    
    def _get_client(self):
        """Get or create the Anthropic client."""
        if self._client is None:
            if anthropic is None:
                raise ImportError(
                    "anthropic package not installed. "
                    "Run: pip install anthropic"
                )
            if not self.settings.anthropic_api_key:
                raise ValueError("ANTHROPIC_API_KEY not configured")
            self._client = anthropic.Anthropic(api_key=self.settings.anthropic_api_key)
        return self._client
    
    async def generate_prompts(
        self,
        comic_script: list,
        style_reference_image: Optional[bytes] = None,
        temperature: float = 0.3,
        target_panel_count: Optional[int] = None,
        progress_callback: Optional[Callable[[float, str], None]] = None
    ) -> ClaudeResult:
        """
        Generate comic panel prompts using the three-pass architecture.
        
        Args:
            comic_script: List of transcript segments with timing info
            style_reference_image: Optional reference image bytes for style analysis
            temperature: Generation temperature (0.3 recommended for consistency)
            target_panel_count: Optional target number of panels to generate
            progress_callback: Optional callback function(progress, message) for progress updates
        
        Returns:
            ClaudeResult with generated prompts or error
        """
        try:
            # Pass 1: Style Analysis (if image provided)
            style_keywords = ""
            if style_reference_image:
                if progress_callback:
                    progress_callback(0.1, "Analyzing style reference...")
                style_keywords = await self._analyze_style_reference(
                    style_reference_image
                )
            
            # Pass 2: Character Sheet Extraction
            if progress_callback:
                progress_callback(0.3, "Extracting character descriptions...")
            character_sheet = await self._extract_character_sheet(
                comic_script, 
                temperature
            )
            
            # Pass 3: Panel Prompt Generation
            if progress_callback:
                progress_callback(0.5, "Generating panel prompts...")
            internal_response = await self._generate_panel_prompts(
                comic_script,
                character_sheet,
                style_keywords,
                temperature,
                target_panel_count=target_panel_count,
                progress_callback=progress_callback
            )
            
            # Post-process: Inject character descriptions
            final_response = self._construct_final_prompts(
                internal_response,
                character_sheet,
                style_keywords
            )
            
            return ClaudeResult(
                success=True,
                response=final_response,
                style_keywords=style_keywords,
                character_sheet=character_sheet
            )
            
        except Exception as e:
            return ClaudeResult(
                success=False,
                error_message=str(e)
            )
    
    async def _analyze_style_reference(
        self,
        image_bytes: bytes
    ) -> str:
        """
        Analyze a reference image to extract prompt-engineering keywords.
        
        Args:
            image_bytes: Raw image bytes (PNG, JPEG, or WebP)
        
        Returns:
            Comma-separated style keywords for Gemini
        """
        client = self._get_client()
        
        # Encode image to base64
        image_base64 = base64.b64encode(image_bytes).decode("utf-8")
        
        # Detect media type (simple detection)
        if image_bytes[:8] == b'\x89PNG\r\n\x1a\n':
            media_type = "image/png"
        elif image_bytes[:2] == b'\xff\xd8':
            media_type = "image/jpeg"
        elif image_bytes[:4] == b'RIFF' and image_bytes[8:12] == b'WEBP':
            media_type = "image/webp"
        else:
            media_type = "image/png"  # Default
        
        response = client.messages.create(
            model=self.settings.claude_model,
            max_tokens=500,
            temperature=0.3,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": image_base64
                            }
                        },
                        {
                            "type": "text",
                            "text": STYLE_ANALYSIS_PROMPT
                        }
                    ]
                }
            ]
        )
        
        # Extract text response
        style_keywords = response.content[0].text.strip()
        return style_keywords
    
    async def _extract_character_sheet(
        self,
        comic_script: list,
        temperature: float
    ) -> Dict[str, str]:
        """
        Extract character sheet from comic script.
        
        Args:
            comic_script: List of transcript segments
            temperature: Generation temperature
        
        Returns:
            Dictionary mapping character names to visual descriptions
        """
        client = self._get_client()
        
        # Format script for analysis
        script_text = self._format_script_for_analysis(comic_script)
        
        # Define tool for structured output
        character_sheet_tool = {
            "name": "extract_characters",
            "description": "Extract all characters with their visual descriptions",
            "input_schema": CharacterSheetResponse.model_json_schema()
        }
        
        response = client.messages.create(
            model=self.settings.claude_model,
            max_tokens=2048,
            temperature=temperature,
            tools=[character_sheet_tool],
            tool_choice={"type": "tool", "name": "extract_characters"},
            messages=[
                {
                    "role": "user",
                    "content": f"{CHARACTER_SHEET_PROMPT}\n\nScript:\n{script_text}"
                }
            ]
        )
        
        # Extract structured output from tool use
        for block in response.content:
            if block.type == "tool_use" and block.name == "extract_characters":
                result = CharacterSheetResponse(**block.input)
                return result.characters
        
        # Fallback: return empty dict if tool use failed
        return {}
    
    def _validate_and_fix_response(self, raw_input: dict) -> ComicGenerationInternalResponse:
        """
        Validate Claude response and provide defaults for missing fields.
        
        Args:
            raw_input: Raw dictionary from Claude's tool use response
        
        Returns:
            Validated ComicGenerationInternalResponse
        
        Raises:
            ValueError: If response cannot be validated even with defaults
        """
        # Make a copy to avoid mutating the original
        fixed_input = raw_input.copy() if isinstance(raw_input, dict) else {}
        
        # Ensure panels field exists
        if "panels" not in fixed_input or fixed_input.get("panels") is None:
            self.logger.warning("Claude response missing 'panels' field, using empty list")
            fixed_input["panels"] = []
        elif not isinstance(fixed_input.get("panels"), list):
            self.logger.warning(f"Claude response 'panels' field is not a list (type: {type(fixed_input.get('panels'))}), converting to list")
            fixed_input["panels"] = []
        
        # Ensure other required fields have defaults
        if "characters" not in fixed_input:
            self.logger.warning("Claude response missing 'characters' field, using empty dict")
            fixed_input["characters"] = {}
        if "global_style" not in fixed_input:
            self.logger.warning("Claude response missing 'global_style' field, using default")
            fixed_input["global_style"] = "comic book style"
        if "global_mood" not in fixed_input:
            self.logger.warning("Claude response missing 'global_mood' field, using default")
            fixed_input["global_mood"] = "neutral"
        
        try:
            return ComicGenerationInternalResponse(**fixed_input)
        except Exception as e:
            # Log what we received for debugging
            received_fields = list(fixed_input.keys()) if isinstance(fixed_input, dict) else []
            self.logger.error(f"Validation error after applying defaults: {e}")
            self.logger.error(f"Received fields: {received_fields}")
            self.logger.error(f"Full input data: {json.dumps(fixed_input, indent=2, default=str)}")
            raise ValueError(
                f"Claude response validation failed. "
                f"Received fields: {received_fields}. "
                f"Error: {str(e)}"
            ) from e
    
    async def _generate_panel_prompts(
        self,
        comic_script: list,
        character_sheet: Dict[str, str],
        style_keywords: str,
        temperature: float,
        target_panel_count: Optional[int] = None,
        progress_callback: Optional[Callable[[float, str], None]] = None
    ) -> ComicGenerationInternalResponse:
        """
        Generate panel prompts with structured output via Tool Use.
        
        Args:
            comic_script: List of transcript segments
            character_sheet: Character name -> description mapping
            style_keywords: Comma-separated style keywords
            temperature: Generation temperature
            target_panel_count: Optional target number of panels to generate
            progress_callback: Optional callback for progress updates
        
        Returns:
            Internal response with panels containing characters_present list
        """
        client = self._get_client()
        
        # Format inputs
        script_text = self._format_script_for_analysis(comic_script)
        character_sheet_text = json.dumps(character_sheet, indent=2)
        
        # Build system prompt
        system_prompt = PANEL_GENERATION_PROMPT.format(
            character_sheet=character_sheet_text,
            style_keywords=style_keywords if style_keywords else "natural, balanced lighting"
        )
        
        # Determine panel count
        if target_panel_count:
            panel_count_text = f"Generate approximately {target_panel_count} panel prompts to cover this entire story. Each panel represents a key moment or scene."
        else:
            # Fallback: calculate from script length
            segments = [item for item in comic_script if isinstance(item, dict) and item.get("_type") not in ["metadata", "full_transcript"]]
            estimated_panels = max(4, len(segments) // 2)
            panel_count_text = f"Generate approximately {estimated_panels} panel prompts to cover this entire story. Each panel represents a key moment or scene."
        
        if progress_callback:
            progress_callback(0.7, f"Requesting {target_panel_count or estimated_panels} panel prompts from Claude...")
        
        # Define tool for structured output
        panel_generation_tool = {
            "name": "generate_comic_panels",
            "description": "Generate comic panel prompts with character consistency",
            "input_schema": ComicGenerationInternalResponse.model_json_schema()
        }
        
        response = client.messages.create(
            model=self.settings.claude_model,
            max_tokens=self.settings.claude_max_tokens,
            temperature=temperature,
            tools=[panel_generation_tool],
            tool_choice={"type": "tool", "name": "generate_comic_panels"},
            messages=[
                {
                    "role": "user",
                    "content": f"{system_prompt}\n\nComic Script:\n{script_text}\n\n{panel_count_text}"
                }
            ]
        )
        
        if progress_callback:
            progress_callback(0.9, "Processing panel prompts...")
        
        # Extract structured output from tool use
        for block in response.content:
            if block.type == "tool_use" and block.name == "generate_comic_panels":
                try:
                    # Log what we received for debugging
                    self.logger.debug(f"Claude tool use response received")
                    if hasattr(block, 'input'):
                        self.logger.debug(f"Response keys: {list(block.input.keys()) if isinstance(block.input, dict) else 'not a dict'}")
                    
                    # Validate and create response with error handling
                    return self._validate_and_fix_response(block.input)
                except Exception as e:
                    # Log the actual input for debugging
                    self.logger.error(f"Validation error: {e}")
                    if hasattr(block, 'input'):
                        received_fields = list(block.input.keys()) if isinstance(block.input, dict) else []
                        self.logger.error(f"Received fields: {received_fields}")
                        self.logger.error(f"Received data (first 1000 chars): {str(block.input)[:1000]}")
                    
                    # Check if panels field is missing
                    error_str = str(e).lower()
                    if "panels" in error_str or "missing" in error_str:
                        # Try to provide a helpful error
                        received_fields = list(block.input.keys()) if isinstance(block.input, dict) else []
                        raise ValueError(
                            f"Claude response missing required 'panels' field. "
                            f"Received fields: {received_fields}. "
                            f"This may indicate the story is too long or Claude hit token limits. "
                            f"Full error: {str(e)}"
                        ) from e
                    raise
        
        # Fallback: raise error if tool use failed
        if response.content:
            # Log what we actually got
            content_types = [block.type for block in response.content]
            self.logger.error(f"Claude did not return expected tool_use block. Content types: {content_types}")
            raise ValueError(
                f"Claude did not return structured panel prompts. "
                f"Response content types: {content_types}. "
                f"Expected tool_use block with name 'generate_comic_panels'."
            )
        raise ValueError("Claude returned empty response")
    
    def _construct_final_prompts(
        self,
        internal_response: ComicGenerationInternalResponse,
        character_sheet: Dict[str, str],
        style_keywords: str
    ) -> ComicGenerationResponse:
        """
        Post-process panel prompts to inject character descriptions.
        
        CRITICAL: Uses characters_present list (structured data), NOT string matching.
        Works even if scene_description uses pronouns.
        
        Args:
            internal_response: Response from Claude with characters_present lists
            character_sheet: Character name -> description mapping
            style_keywords: Comma-separated style keywords
        
        Returns:
            Final response with fully constructed prompts
        """
        final_panels = []
        
        for panel in internal_response.panels:
            # Get character descriptions for all characters in this panel
            character_descriptions = []
            for char_name in panel.characters_present:
                if char_name in character_sheet:
                    desc = character_sheet[char_name]
                    character_descriptions.append(f"{char_name} ({desc})")
            
            # Construct: [Character descriptions]. [Scene]. [Style]
            parts = []
            
            if character_descriptions:
                parts.append(", ".join(character_descriptions))
            
            parts.append(panel.scene_description)
            
            if style_keywords:
                parts.append(style_keywords)
            
            final_prompt = ". ".join(parts)
            if not final_prompt.endswith("."):
                final_prompt += "."
            
            final_panels.append(PanelPrompt(
                panel_id=panel.panel_id,
                prompt=final_prompt,
                negative_prompt=panel.negative_prompt,
                mood=panel.mood,
                camera_angle=panel.camera_angle,
                start_s=panel.start_s,
                end_s=panel.end_s
            ))
        
        return ComicGenerationResponse(
            characters=character_sheet,
            global_style=internal_response.global_style,
            global_mood=internal_response.global_mood,
            panels=final_panels
        )
    
    def _format_script_for_analysis(self, comic_script: list) -> str:
        """
        Format comic script segments into readable text for Claude.
        
        Args:
            comic_script: List of transcript segments
        
        Returns:
            Formatted script text
        """
        lines = []
        
        for item in comic_script:
            if isinstance(item, dict):
                # Skip metadata entries
                if item.get("_type") in ["metadata", "full_transcript"]:
                    if item.get("_type") == "full_transcript":
                        lines.append(f"[Full transcript: {item.get('text', '')}]")
                    continue
                
                # Format segment with timing
                start = item.get("start_s", 0)
                end = item.get("end_s", 0)
                text = item.get("lyric_snippet", "") or item.get("text", "")
                
                if text:
                    lines.append(f"[{start:.1f}s - {end:.1f}s]: {text}")
        
        return "\n".join(lines) if lines else str(comic_script)


# Global service instance
claude_prompt_service = ClaudePromptService()
