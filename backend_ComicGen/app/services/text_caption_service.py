"""
Text Caption Service for Comic Pages.

Matches transcript segments to panels and adds story text captions
at the bottom of each comic page.
"""

import base64
import io
import logging
from typing import Dict, List, Optional

try:
    from PIL import Image, ImageDraw, ImageFont
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False


def _get_timing_value(data: dict, key: str, default: float = 0.0) -> float:
    """
    Safely extract timing value, converting None to default.
    
    Args:
        data: Dictionary containing timing data
        key: Key to extract (e.g., "start_s", "end_s")
        default: Default value to use if key is missing or None
    
    Returns:
        Float value, or default if key is missing/None/invalid
    """
    value = data.get(key, default)
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def match_transcript_to_panels(
    panels: List[dict], 
    transcript: List[dict]
) -> Dict[int, str]:
    """
    Match transcript segments to panels by timing overlap.
    
    Args:
        panels: List of panel dictionaries with panel_id, start_s, end_s
        transcript: List of transcript segments with start_s, end_s, lyric_snippet/text
    
    Returns:
        Dict mapping panel_id -> combined text from overlapping segments
    """
    panel_texts = {}
    
    for panel in panels:
        panel_id = panel.get("panel_id")
        
        if panel_id is None:
            continue
        
        # Safely extract timing values, converting None to 0.0
        panel_start = _get_timing_value(panel, "start_s", 0.0)
        panel_end = _get_timing_value(panel, "end_s", 0.0)
        
        # Skip panels without valid timing (both are 0 or None)
        if panel_start == 0.0 and panel_end == 0.0:
            continue
        
        # Find transcript segments that overlap with this panel's timing
        matching_segments = []
        for segment in transcript:
            # Skip metadata entries
            if isinstance(segment, dict) and segment.get("_type") in ["metadata", "full_transcript"]:
                continue
            
            # Safely extract timing values, converting None to 0.0
            seg_start = _get_timing_value(segment, "start_s", 0.0)
            seg_end = _get_timing_value(segment, "end_s", 0.0)
            
            # Skip segments without valid timing (both are 0 or None)
            if seg_start == 0.0 and seg_end == 0.0:
                continue
            
            # Check for overlap: segments overlap if not (seg_end < panel_start or seg_start > panel_end)
            # Now safe to compare since all values are guaranteed to be floats
            if not (seg_end < panel_start or seg_start > panel_end):
                text = segment.get("lyric_snippet") or segment.get("text", "")
                if text and text.strip():
                    matching_segments.append(text.strip())
        
        # Combine matching segments into single text
        combined_text = " ".join(matching_segments)
        panel_texts[panel_id] = combined_text
    
    return panel_texts


def _calculate_panel_layout(num_panels: int) -> tuple:
    """
    Calculate grid layout for panels.
    
    Args:
        num_panels: Number of panels
    
    Returns:
        (rows, cols) tuple
    """
    if num_panels == 4:
        return (2, 2)
    elif num_panels == 5:
        return (2, 3)  # 2 rows, 3 cols (one panel spans)
    elif num_panels == 6:
        return (2, 3)
    else:
        # Default: try to make square-ish
        cols = int(num_panels ** 0.5) + 1
        rows = (num_panels + cols - 1) // cols
        return (rows, cols)


def _calculate_panel_positions(img_width: int, img_height: int, num_panels: int) -> List[dict]:
    """
    Calculate position and size of each panel in the grid.
    
    Args:
        img_width: Image width
        img_height: Image height
        num_panels: Number of panels
    
    Returns:
        List of dicts with 'x', 'y', 'width', 'height' for each panel
    """
    rows, cols = _calculate_panel_layout(num_panels)
    panel_width = img_width // cols
    panel_height = img_height // rows
    
    positions = []
    for i in range(num_panels):
        row = i // cols
        col = i % cols
        x = col * panel_width
        y = row * panel_height
        positions.append({
            'x': x,
            'y': y,
            'width': panel_width,
            'height': panel_height
        })
    
    return positions


def _get_font(size: int, bold: bool = False):
    """Try to load a font, fallback to default."""
    if not PIL_AVAILABLE:
        return None
    
    font_paths = [
        # macOS
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        # Linux
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        # Windows
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
    ]
    
    for font_path in font_paths:
        try:
            return ImageFont.truetype(font_path, size)
        except (OSError, IOError):
            continue
    
    # Fallback to default font
    try:
        return ImageFont.load_default()
    except:
        return None


async def generate_page_story_summary(
    panels: List[dict],
    panel_texts: Dict[int, str],
    anthropic_api_key: Optional[str] = None
) -> Optional[str]:
    """
    Generate a narrative story summary for an entire page using Claude 3.5 Haiku.
    
    Args:
        panels: List of panel dictionaries with prompts
        panel_texts: Dict mapping panel_id -> transcript text
        anthropic_api_key: Anthropic API key (if None, will try to get from environment)
    
    Returns:
        Single narrative summary string describing the page, or None if generation fails
    """
    if not ANTHROPIC_AVAILABLE:
        logger = logging.getLogger(__name__)
        logger.warning("Anthropic library not available. Cannot generate page story summary.")
        return None
    
    try:
        # Get API key from parameter or environment
        if not anthropic_api_key:
            import os
            anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
        
        if not anthropic_api_key:
            logger = logging.getLogger(__name__)
            logger.warning("ANTHROPIC_API_KEY not configured. Cannot generate page story summary.")
            return None
        
        # Create client
        client = anthropic.Anthropic(api_key=anthropic_api_key)
        
        # Build panel descriptions
        panel_descriptions = []
        for i, panel in enumerate(panels, 1):
            prompt = panel.get("prompt", "")
            panel_descriptions.append(f"Panel {i}: {prompt}")
        
        # Combine transcript texts for context
        transcript_texts = []
        for panel in panels:
            panel_id = panel.get("panel_id")
            if panel_id and panel_id in panel_texts:
                text = panel_texts[panel_id]
                if text and text.strip():
                    transcript_texts.append(text.strip())
        
        combined_transcript = " ".join(transcript_texts) if transcript_texts else ""
        
        # Build prompt
        prompt = f"""Based on the following comic panels, write a brief narrative summary (2-4 sentences) describing what happens on this page. Write it as a cohesive story in third person, past tense.

Panel descriptions:
{chr(10).join(panel_descriptions)}

Transcript text for context:
{combined_transcript if combined_transcript else "No transcript text available"}

Write a single flowing narrative that describes the events on this page. Be concise but descriptive."""
        
        # Call Claude 3.5 Haiku
        response = client.messages.create(
            model="claude-3-5-haiku-20241022",
            max_tokens=200,
            temperature=0.7,
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )
        
        # Extract text from response
        if response.content and len(response.content) > 0:
            summary_text = response.content[0].text.strip()
            return summary_text
        
        return None
        
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.warning(f"Failed to generate page story summary: {e}")
        return None


def add_page_story_summary(
    image_base64: str,
    story_summary: str,
    num_panels: int
) -> str:
    """
    Add a single page-level story summary underneath all panels.
    
    Args:
        image_base64: Base64-encoded image
        story_summary: Narrative summary text for the page
        num_panels: Number of panels on the page (for layout calculation)
    
    Returns:
        Base64-encoded image with story summary added at bottom
    """
    if not PIL_AVAILABLE:
        # If Pillow not available, return original image
        return image_base64
    
    if not story_summary or not story_summary.strip():
        # If no summary, return original image
        return image_base64
    
    # Decode image
    image_data = base64.b64decode(image_base64)
    img = Image.open(io.BytesIO(image_data))
    img_width, img_height = img.size
    
    # Create new image with space for summary at bottom
    # Summary area: ~150-200px height to accommodate 3-5 lines
    summary_height = 200
    new_height = img_height + summary_height
    
    new_img = Image.new('RGB', (img_width, new_height), 'white')
    new_img.paste(img, (0, 0))
    
    # Draw summary text
    draw = ImageDraw.Draw(new_img)
    
    # Load font (14-16px for readability)
    font = _get_font(15, bold=False)
    if not font:
        font = _get_font(14, bold=False)
    
    # Text positioning
    margin = 20
    text_x = margin
    text_y = img_height + margin
    max_width = img_width - (margin * 2)  # Full width minus margins
    
    # Wrap text to fit within available width
    words = story_summary.split()
    lines = []
    current_line = ""
    
    for word in words:
        test_line = current_line + " " + word if current_line else word
        if font:
            bbox = draw.textbbox((0, 0), test_line, font=font)
            text_width = bbox[2] - bbox[0]
        else:
            # Rough estimate: ~8 pixels per character for 15px font
            text_width = len(test_line) * 8
        
        if text_width < max_width:
            current_line = test_line
        else:
            if current_line:
                lines.append(current_line)
            # Handle long words
            if font:
                word_bbox = draw.textbbox((0, 0), word, font=font)
                word_width = word_bbox[2] - word_bbox[0]
                if word_width > max_width:
                    # Break long word
                    word_chunks = []
                    remaining_word = word
                    while remaining_word:
                        chunk = ""
                        for char in remaining_word:
                            test_chunk = chunk + char
                            test_bbox = draw.textbbox((0, 0), test_chunk, font=font)
                            if (test_bbox[2] - test_bbox[0]) <= max_width:
                                chunk = test_chunk
                            else:
                                break
                        if chunk:
                            word_chunks.append(chunk)
                            remaining_word = remaining_word[len(chunk):]
                        else:
                            word_chunks.append(remaining_word[0])
                            remaining_word = remaining_word[1:]
                    current_line = word_chunks[0] if word_chunks else word
                    for chunk in word_chunks[1:]:
                        lines.append(chunk)
                else:
                    current_line = word
            else:
                # Rough estimate
                if len(word) * 8 > max_width:
                    chunk_size = max_width // 8
                    word_chunks = [word[j:j+chunk_size] for j in range(0, len(word), chunk_size)]
                    current_line = word_chunks[0] if word_chunks else word
                    for chunk in word_chunks[1:]:
                        lines.append(chunk)
                else:
                    current_line = word
    
    if current_line:
        lines.append(current_line)
    
    # Draw wrapped text (limit to ~5 lines to fit in summary area)
    line_height = 24  # 1.5x line spacing for 15px font
    max_lines = min(len(lines), 5)  # Limit to 5 lines
    
    for i, line in enumerate(lines[:max_lines]):
        line_y = text_y + (i * line_height)
        if font:
            draw.text((text_x, line_y), line, fill='black', font=font)
        else:
            draw.text((text_x, line_y), line, fill='black')
    
    # Encode back to base64
    buffer = io.BytesIO()
    new_img.save(buffer, format='PNG')
    return base64.b64encode(buffer.getvalue()).decode('utf-8')


# Keep old function name for backward compatibility (deprecated)
def add_text_captions_to_page(
    image_base64: str,
    panels: List[dict],
    panel_texts: Dict[int, str],
    num_panels: int
) -> str:
    """
    DEPRECATED: Use add_page_story_summary() instead.
    
    This function is kept for backward compatibility but should not be used.
    """
    # Fallback: if no panel texts, return original
    if not panel_texts:
        return image_base64
    
    # Simple fallback: combine all panel texts
    combined_text = " ".join([text for text in panel_texts.values() if text])
    if combined_text:
        return add_page_story_summary(image_base64, combined_text, num_panels)
    
    return image_base64
