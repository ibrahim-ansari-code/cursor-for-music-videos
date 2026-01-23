"""
Text Caption Service for Comic Pages.

Matches transcript segments to panels and adds story text captions
at the bottom of each comic page.
"""

import base64
import io
from typing import Dict, List, Optional

try:
    from PIL import Image, ImageDraw, ImageFont
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


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


def add_text_captions_to_page(
    image_base64: str,
    panels: List[dict],
    panel_texts: Dict[int, str],
    num_panels: int
) -> str:
    """
    Add text caption area at bottom of page with panel dialogue/narration.
    
    Args:
        image_base64: Base64-encoded image
        panels: List of panel data with panel_id
        panel_texts: Dict mapping panel_id -> text
        num_panels: Number of panels on the page
    
    Returns:
        Base64-encoded image with text captions added
    """
    if not PIL_AVAILABLE:
        # If Pillow not available, return original image
        return image_base64
    
    # Decode image
    image_data = base64.b64decode(image_base64)
    img = Image.open(io.BytesIO(image_data))
    img_width, img_height = img.size
    
    # Calculate caption area height (18% of image height, minimum 100px)
    caption_height = max(int(img_height * 0.18), 100)
    
    # Create new image with caption area
    new_img = Image.new('RGB', (img_width, img_height + caption_height), 'white')
    new_img.paste(img, (0, 0))
    
    # Draw caption area
    draw = ImageDraw.Draw(new_img)
    
    # Load fonts
    font_small = _get_font(12, bold=False)
    font_bold = _get_font(14, bold=True)
    
    # Add text for each panel
    caption_y = img_height + 15
    panel_width = img_width // num_panels
    
    for i, panel in enumerate(panels):
        panel_id = panel.get("panel_id", i + 1)
        text = panel_texts.get(panel_id, "")
        
        if not text:
            continue
        
        # Calculate position for this panel's caption
        x = (i * panel_width) + 15
        y = caption_y
        max_width = panel_width - 30  # Leave margins
        
        # Truncate very long text (will wrap anyway, but limit initial length)
        if len(text) > 200:
            text = text[:200] + "..."
        
        # Draw panel label
        if font_bold:
            draw.text((x, y), f"Panel {i+1}:", fill='black', font=font_bold)
        else:
            draw.text((x, y), f"Panel {i+1}:", fill='black', font=font_small)
        
        # Wrap text to fit within panel width
        words = text.split()
        lines = []
        current_line = ""
        
        for word in words:
            test_line = current_line + " " + word if current_line else word
            if font_small:
                bbox = draw.textbbox((0, 0), test_line, font=font_small)
                text_width = bbox[2] - bbox[0]
            else:
                # Rough estimate: ~6 pixels per character
                text_width = len(test_line) * 6
            
            if text_width < max_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                # If single word is too long, truncate it
                if font_small:
                    word_bbox = draw.textbbox((0, 0), word, font=font_small)
                    word_width = word_bbox[2] - word_bbox[0]
                    if word_width > max_width:
                        # Truncate long word character by character
                        truncated_word = word
                        while truncated_word:
                            test_bbox = draw.textbbox((0, 0), truncated_word + "...", font=font_small)
                            if (test_bbox[2] - test_bbox[0]) <= max_width:
                                break
                            truncated_word = truncated_word[:-1]
                        current_line = truncated_word + "..." if truncated_word else "..."
                    else:
                        current_line = word
                else:
                    # Rough estimate: ~6 pixels per character
                    if len(word) * 6 > max_width:
                        max_chars = max_width // 6
                        current_line = word[:max_chars] + "..." if max_chars > 0 else "..."
                    else:
                        current_line = word
        
        if current_line:
            lines.append(current_line)
        
        # Draw wrapped text (max 3 lines to fit in caption area)
        line_y = y + 20
        for line in lines[:3]:
            if font_small:
                draw.text((x, line_y), line, fill='black', font=font_small)
            else:
                draw.text((x, line_y), line, fill='black')
            line_y += 18
    
    # Encode back to base64
    buffer = io.BytesIO()
    new_img.save(buffer, format='PNG')
    return base64.b64encode(buffer.getvalue()).decode('utf-8')
