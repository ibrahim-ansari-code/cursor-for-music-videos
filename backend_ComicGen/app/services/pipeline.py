"""
Pipeline Orchestrator for Audio to Comic Generation.

Coordinates the full pipeline:
1. Audio transcription (via ElevenLabs)
2. Prompt generation (via Claude)
3. Image generation (via Gemini)
"""

import asyncio
import time
from pathlib import Path
from typing import Optional, List, Callable
from dataclasses import dataclass, field

from app.services.gemini_service import gemini_service, PanelResult
from app.services.claude_prompt_service import claude_prompt_service, ClaudeResult
from app.services.text_caption_service import add_text_captions_to_page, match_transcript_to_panels


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class PipelineConfig:
    """Configuration for pipeline execution."""
    output_dir: Path = field(default_factory=lambda: Path("/tmp/pipeline_output"))
    image_style: str = "storybook"
    aspect_ratio: str = "16:9"
    save_images: bool = True
    save_metadata: bool = True
    style_reference_image: Optional[bytes] = None
    prompt_temperature: float = 0.3
    num_panels: int = 6
    image_temperature: float = 0.2
    panels_per_page: int = 5
    min_panels_per_page: int = 4
    max_panels_per_page: int = 6


@dataclass
class PipelineResult:
    """Result from pipeline execution."""
    success: bool
    total_panels: int = 0
    total_pages: int = 0
    successful_images: int = 0
    failed_images: int = 0
    successful_pages: int = 0
    failed_pages: int = 0
    panels: List[dict] = field(default_factory=list)
    pages: List[dict] = field(default_factory=list)
    execution_time_s: float = 0.0
    error_message: Optional[str] = None
    # Backward compatibility
    gumloop_run_id: Optional[str] = None


# ============================================================================
# Constants
# ============================================================================

# Maximum panels to generate per request (prevents token limit issues)
MAX_PANELS_PER_REQUEST = 40

# ============================================================================
# Pipeline Orchestrator
# ============================================================================

class PipelineOrchestrator:
    """
    Orchestrates the audio-to-comic pipeline.
    
    Flow:
    1. Receive comic script (transcribed audio)
    2. Generate prompts using Claude (with style reference if provided)
    3. Group panels into pages
    4. Generate multi-panel comic pages using Gemini
    5. Return results
    """
    
    def __init__(self):
        self.gemini = gemini_service
        self.claude = claude_prompt_service
    
    def is_configured(self) -> bool:
        """Check if all required services are configured."""
        return self.gemini.is_configured() and self.claude.is_configured()
    
    def _emit_progress(
        self,
        callback: Optional[Callable[[str, float, str], None]],
        stage: str,
        progress: float,
        message: str
    ):
        """Helper to emit progress updates if callback is provided."""
        if callback:
            callback(stage, progress, message)
    
    def _group_panels_into_pages(
        self,
        panels: List[dict],
        panels_per_page: int = 5
    ) -> List[List[dict]]:
        """Group panel prompts into pages with 4-6 panels per page."""
        pages = []
        for i in range(0, len(panels), panels_per_page):
            page_panels = panels[i:i+panels_per_page]
            pages.append(page_panels)
        return pages
    
    async def run_from_transcript(
        self,
        comic_script: list,
        config: Optional[PipelineConfig] = None,
        progress_callback: Optional[Callable[[str, float, str], None]] = None
    ) -> PipelineResult:
        """
        Run the pipeline from a comic script transcript.
        
        Args:
            comic_script: List of transcript segments with timing info (includes transcript data)
            config: Pipeline configuration options
            progress_callback: Optional callback function(stage, progress, message) for progress updates
        
        Returns:
            PipelineResult with generated comic pages
        """
        """
        Run the pipeline from a comic script transcript.
        
        Args:
            comic_script: List of transcript segments with timing info
            config: Pipeline configuration options
            progress_callback: Optional callback function(stage, progress, message) for progress updates
        
        Returns:
            PipelineResult with generated comic pages
        """
        start_time = time.time()
        config = config or PipelineConfig()
        
        try:
            # Validate services
            if not self.claude.is_configured():
                return PipelineResult(
                    success=False,
                    error_message="Claude API not configured. Set ANTHROPIC_API_KEY."
                )
            
            if not self.gemini.is_configured():
                return PipelineResult(
                    success=False,
                    error_message="Gemini API not configured. Set GEMINI_API_KEY or GOOGLE_API_KEY."
                )
            
            # Step 1: Analyze story and calculate panel count
            self._emit_progress(progress_callback, "analyzing_story", 5, "Analyzing story length...")
            
            # Calculate duration from transcript
            duration_seconds = 0.0
            segments = [item for item in comic_script if isinstance(item, dict) and item.get("_type") not in ["metadata", "full_transcript"]]
            if segments:
                last_segment = segments[-1]
                duration_seconds = last_segment.get("end_s", 0.0)
            
            # Calculate panel count: 1 panel per ~10 seconds, minimum 4, maximum 40
            calculated_panels = max(4, int(duration_seconds / 10)) if duration_seconds > 0 else max(4, len(segments) // 2)
            total_panels = min(calculated_panels, MAX_PANELS_PER_REQUEST)
            
            # Update progress message to indicate if cap was applied
            if calculated_panels > MAX_PANELS_PER_REQUEST:
                self._emit_progress(progress_callback, "analyzing_story", 10, 
                    f"Story will have {total_panels} panels (capped from {calculated_panels} to stay within token limits)")
            else:
                self._emit_progress(progress_callback, "analyzing_story", 10, 
                    f"Story will have {total_panels} panels")
            
            # Step 2: Generate prompts with Claude
            self._emit_progress(progress_callback, "extracting_characters", 15, "Extracting character descriptions...")
            
            claude_result = await self.claude.generate_prompts(
                comic_script=comic_script,
                style_reference_image=config.style_reference_image,
                temperature=config.prompt_temperature,
                target_panel_count=total_panels,
                progress_callback=lambda p, m: self._emit_progress(
                    progress_callback, 
                    "generating_panel_prompts", 
                    15 + (p * 0.25),  # 15-40% range
                    m
                )
            )
            
            if not claude_result.success or not claude_result.response:
                return PipelineResult(
                    success=False,
                    error_message=f"Prompt generation failed: {claude_result.error_message}"
                )
            
            # Check if panels list is empty
            if not claude_result.response.panels or len(claude_result.response.panels) == 0:
                return PipelineResult(
                    success=False,
                    error_message=f"Claude did not generate any panel prompts. This may indicate the story is too long (exceeds {MAX_PANELS_PER_REQUEST} panel limit), token limits were reached, or the story content was not suitable for comic generation."
                )
            
            num_characters = len(claude_result.character_sheet) if claude_result.character_sheet else 0
            self._emit_progress(progress_callback, "extracting_characters", 20, f"Found {num_characters} characters")
            self._emit_progress(progress_callback, "generating_panel_prompts", 40, f"Generated {len(claude_result.response.panels)} panel prompts")
            
            # Step 3: Prepare prompts for image generation
            panel_prompts = []
            for panel in claude_result.response.panels:
                panel_prompts.append({
                    "panel_id": panel.panel_id,
                    "prompt": panel.prompt,
                    "negative_prompt": panel.negative_prompt,
                    "mood": panel.mood,
                    "camera_angle": panel.camera_angle,
                    "start_s": panel.start_s,
                    "end_s": panel.end_s
                })
            
            # Step 4: Group panels into pages
            self._emit_progress(progress_callback, "grouping_pages", 45, "Organizing panels into pages...")
            
            # Ensure panels_per_page is within valid range
            panels_per_page = max(config.min_panels_per_page, min(config.max_panels_per_page, config.panels_per_page))
            page_groups = self._group_panels_into_pages(panel_prompts, panels_per_page)
            num_pages = len(page_groups)
            
            self._emit_progress(progress_callback, "grouping_pages", 50, f"Organized into {num_pages} pages")
            
            # Step 4.5: Match transcript to panels for text captions
            panel_texts = match_transcript_to_panels(panel_prompts, comic_script)
            
            # Step 5: Generate comic pages (multi-panel images)
            pages = []
            successful_pages = 0
            failed_pages = 0
            all_panels = []  # For backward compatibility
            
            for page_num, page_panels in enumerate(page_groups, 1):
                progress_pct = 50 + ((page_num / num_pages) * 45)  # 50-95% range
                self._emit_progress(
                    progress_callback,
                    "generating_pages",
                    progress_pct,
                    f"Generating page {page_num} of {num_pages}..."
                )
                
                # Generate single multi-panel page image
                page_result = await self.gemini.generate_comic_page(
                    panel_prompts=page_panels,
                    page_number=page_num,
                    style=config.image_style,
                    aspect_ratio=config.aspect_ratio,
                    temperature=config.image_temperature
                )
                
                if page_result.success:
                    successful_pages += 1
                    
                    # Add text captions to page image
                    image_with_captions = page_result.image_base64
                    if page_result.image_base64:
                        try:
                            image_with_captions = add_text_captions_to_page(
                                image_base64=page_result.image_base64,
                                panels=page_panels,
                                panel_texts=panel_texts,
                                num_panels=len(page_panels)
                            )
                        except Exception as e:
                            # If caption addition fails, use original image
                            # Log error but don't fail the whole page
                            import logging
                            logger = logging.getLogger(__name__)
                            logger.warning(f"Failed to add text captions to page {page_num}: {e}")
                            image_with_captions = page_result.image_base64
                    
                    # Save image if configured
                    file_path = None
                    if config.save_images and image_with_captions:
                        config.output_dir.mkdir(parents=True, exist_ok=True)
                        file_path = config.output_dir / f"page_{page_num:03d}.png"
                        self.gemini.save_image(image_with_captions, file_path)
                    
                    # Create page object
                    page_obj = {
                        "page_number": page_num,
                        "panels": page_panels,  # Store the panel prompts used
                        "image_base64": image_with_captions,  # Use image with captions
                        "mime_type": page_result.mime_type,
                        "success": True,
                        "file_path": str(file_path) if file_path else None
                    }
                    pages.append(page_obj)
                    
                    # For backward compatibility: create individual panel entries
                    for i, panel_data in enumerate(page_panels, 1):
                        all_panels.append({
                            "panel_id": panel_data.get("panel_id", (page_num - 1) * panels_per_page + i),
                            "success": True,
                            "image_base64": image_with_captions,  # Use image with captions
                            "mime_type": page_result.mime_type,
                            "prompt": panel_data.get("prompt", ""),
                            "mood": panel_data.get("mood"),
                            "camera_angle": panel_data.get("camera_angle"),
                            "start_s": panel_data.get("start_s"),
                            "end_s": panel_data.get("end_s"),
                            "page_number": page_num,
                            "file_path": str(file_path) if file_path else None
                        })
                else:
                    failed_pages += 1
                    pages.append({
                        "page_number": page_num,
                        "panels": page_panels,
                        "success": False,
                        "error": page_result.error_message
                    })
                    
                    # Add failed panels for backward compatibility
                    for i, panel_data in enumerate(page_panels, 1):
                        all_panels.append({
                            "panel_id": panel_data.get("panel_id", (page_num - 1) * panels_per_page + i),
                            "success": False,
                            "error": page_result.error_message,
                            "prompt": panel_data.get("prompt", ""),
                            "page_number": page_num
                        })
                
                # Small delay between page generations
                if page_num < num_pages:
                    await asyncio.sleep(0.5)
            
            execution_time = time.time() - start_time
            self._emit_progress(progress_callback, "complete", 100, f"Complete! Generated {num_pages} pages with {len(panel_prompts)} panels")
            
            return PipelineResult(
                success=True,
                total_panels=len(panel_prompts),
                total_pages=num_pages,
                successful_images=len([p for p in all_panels if p.get("success")]),
                failed_images=len([p for p in all_panels if not p.get("success")]),
                successful_pages=successful_pages,
                failed_pages=failed_pages,
                panels=all_panels,  # Backward compatibility
                pages=pages,
                execution_time_s=execution_time,
                gumloop_run_id=None  # Backward compatibility
            )
            
        except Exception as e:
            return PipelineResult(
                success=False,
                error_message=str(e),
                execution_time_s=time.time() - start_time
            )
    
    async def generate_prompts_only(
        self,
        comic_script: list,
        style_reference_image: Optional[bytes] = None,
        temperature: float = 0.3
    ) -> ClaudeResult:
        """
        Generate prompts without image generation.
        
        Useful for testing or when you want to inspect prompts before generation.
        
        Args:
            comic_script: List of transcript segments
            style_reference_image: Optional reference image bytes
            temperature: Generation temperature
        
        Returns:
            ClaudeResult with generated prompts
        """
        return await self.claude.generate_prompts(
            comic_script=comic_script,
            style_reference_image=style_reference_image,
            temperature=temperature
        )


# Global orchestrator instance
pipeline_orchestrator = PipelineOrchestrator()
