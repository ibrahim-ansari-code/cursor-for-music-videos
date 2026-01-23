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


def add_text_captions_to_page(
    image_base64: str,
    panels: List[dict],
    panel_texts: Dict[int, str],
    num_panels: int
) -> str:
    """
    Add text caption areas under each corresponding panel.
    
    Each panel gets its own caption area positioned directly below it.
    
    Args:
        image_base64: Base64-encoded image
        panels: List of panel data with panel_id
        panel_texts: Dict mapping panel_id -> text
        num_panels: Number of panels on the page
    
    Returns:
        Base64-encoded image with text captions added under each panel
    """
    if not PIL_AVAILABLE:
        # If Pillow not available, return original image
        return image_base64
    
    # Decode image
    image_data = base64.b64decode(image_base64)
    img = Image.open(io.BytesIO(image_data))
    img_width, img_height = img.size
    
    # Calculate panel positions from grid layout
    panel_positions = _calculate_panel_positions(img_width, img_height, num_panels)
    
    # Calculate caption height (25% of panel height, or fixed 120px to accommodate more text)
    rows, cols = _calculate_panel_layout(num_panels)
    panel_height = img_height // rows
    caption_height = max(int(panel_height * 0.25), 120)
    
    # Calculate total height needed (original image + caption areas for each row)
    total_caption_height = rows * caption_height
    new_height = img_height + total_caption_height
    
    # Create new image with caption areas
    new_img = Image.new('RGB', (img_width, new_height), 'white')
    new_img.paste(img, (0, 0))
    
    # Draw caption areas
    draw = ImageDraw.Draw(new_img)
    
    # Load fonts
    font_small = _get_font(12, bold=False)
    font_bold = _get_font(14, bold=True)
    
    # Add caption for each panel
    for i, panel in enumerate(panels):
        panel_id = panel.get("panel_id", i + 1)
        text = panel_texts.get(panel_id, "")
        
        if not text:
            continue
        
        # Get panel position
        panel_pos = panel_positions[i]
        panel_x = panel_pos['x']
        panel_y = panel_pos['y']
        panel_width = panel_pos['width']
        panel_height_actual = panel_pos['height']
        
        # Calculate which row this panel is in
        rows, cols = _calculate_panel_layout(num_panels)
        row = i // cols
        
        # Calculate caption position (directly under panel)
        caption_x = panel_x + 10  # Small margin from left
        caption_y = img_height + (row * caption_height) + 10
        max_width = panel_width - 20  # Leave margins
        
        # Draw panel label (bold, visible)
        label_text = f"Panel {i+1}:"
        if font_bold:
            draw.text((caption_x, caption_y), label_text, fill='black', font=font_bold)
        else:
            # Use larger font for label if bold not available
            draw.text((caption_x, caption_y), label_text, fill='black', font=font_small)
        
        # Get label width to position text after label
        if font_bold:
            label_bbox = draw.textbbox((0, 0), label_text, font=font_bold)
            label_width = label_bbox[2] - label_bbox[0]
        else:
            label_bbox = draw.textbbox((0, 0), label_text, font=font_small)
            label_width = label_bbox[2] - label_bbox[0]
        
        # Adjust text start position after label
        text_start_x = caption_x + label_width + 5
        text_max_width = max_width - label_width - 5
        
        # Keep full text - no truncation
        
        # Wrap text to fit within caption width
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
            
            if text_width < text_max_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                # If single word is too long, break it (don't truncate, just wrap)
                if font_small:
                    word_bbox = draw.textbbox((0, 0), word, font=font_small)
                    word_width = word_bbox[2] - word_bbox[0]
                    if word_width > text_max_width:
                        # Break long word by splitting into chunks that fit
                        word_chunks = []
                        remaining_word = word
                        while remaining_word:
                            chunk = ""
                            for char in remaining_word:
                                test_chunk = chunk + char
                                test_bbox = draw.textbbox((0, 0), test_chunk, font=font_small)
                                if (test_bbox[2] - test_bbox[0]) <= text_max_width:
                                    chunk = test_chunk
                                else:
                                    break
                            if chunk:
                                word_chunks.append(chunk)
                                remaining_word = remaining_word[len(chunk):]
                            else:
                                # Single character doesn't fit, add it anyway
                                word_chunks.append(remaining_word[0])
                                remaining_word = remaining_word[1:]
                        current_line = word_chunks[0] if word_chunks else word
                        # Add remaining chunks as separate lines
                        for chunk in word_chunks[1:]:
                            lines.append(chunk)
                    else:
                        current_line = word
                else:
                    # Rough estimate: ~6 pixels per character
                    if len(word) * 6 > text_max_width:
                        # Break word into chunks
                        chunk_size = text_max_width // 6
                        word_chunks = [word[j:j+chunk_size] for j in range(0, len(word), chunk_size)]
                        current_line = word_chunks[0] if word_chunks else word
                        for chunk in word_chunks[1:]:
                            lines.append(chunk)
                    else:
                        current_line = word
        
        if current_line:
            lines.append(current_line)
        
        # Draw wrapped text (allow up to 15 lines to show complete text)
        line_y = caption_y + 18  # Start below label
        for line in lines[:15]:  # Show up to 15 lines instead of 3
            if font_small:
                draw.text((text_start_x, line_y), line, fill='black', font=font_small)
            else:
                draw.text((text_start_x, line_y), line, fill='black')
            line_y += 16
    
    # Encode back to base64
    buffer = io.BytesIO()
    new_img.save(buffer, format='PNG')
    return base64.b64encode(buffer.getvalue()).decode('utf-8')
