#!/usr/bin/env python3
"""
Direct pipeline test - bypasses Gumloop and generates images from transcript.

This script:
1. Reads the comic script JSON
2. Extracts key story moments
3. Generates comic panel images directly with Gemini

Usage:
    python test_direct_pipeline.py output/Santas_Day_Off_*/comicscript.json
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))

from app.services.gemini_service import gemini_service


def extract_story_scenes(comic_script: list) -> list[dict]:
    """
    Extract key story moments from the comic script.
    Groups segments into logical scenes for image generation.
    """
    scenes = []
    
    # Find metadata and full transcript
    metadata = None
    full_transcript = None
    segments = []
    
    for item in comic_script:
        if isinstance(item, dict):
            if item.get("_type") == "metadata":
                metadata = item
            elif item.get("_type") == "full_transcript":
                full_transcript = item.get("text", "")
            elif item.get("id"):
                segments.append(item)
    
    title = metadata.get("title", "Story") if metadata else "Story"
    
    # Group segments into scenes (roughly every 30-40 seconds of content)
    current_scene_text = []
    current_start = 0
    scene_num = 1
    
    for seg in segments:
        text = seg.get("text", "").strip()
        if not text or len(text) < 3:
            continue
            
        start_s = seg.get("start_s", 0)
        end_s = seg.get("end_s", 0)
        
        if not current_scene_text:
            current_start = start_s
        
        current_scene_text.append(text)
        
        # Create a scene every ~30 seconds or when we have enough text
        combined_text = " ".join(current_scene_text)
        if end_s - current_start > 30 or len(combined_text) > 500:
            scenes.append({
                "scene_id": scene_num,
                "text": combined_text[:600],  # Limit prompt length
                "start_s": current_start,
                "end_s": end_s
            })
            current_scene_text = []
            scene_num += 1
    
    # Add remaining text as final scene
    if current_scene_text:
        scenes.append({
            "scene_id": scene_num,
            "text": " ".join(current_scene_text)[:600],
            "start_s": current_start,
            "end_s": segments[-1].get("end_s", 0) if segments else 0
        })
    
    return scenes[:6]  # Limit to 6 scenes for testing


def create_image_prompts(scenes: list[dict], title: str) -> list[dict]:
    """
    Create detailed image prompts from story scenes.
    """
    prompts = []
    
    for scene in scenes:
        # Create a detailed prompt for comic panel generation
        prompt = f"""STORY: {title}

SCENE TO ILLUSTRATE:
{scene['text']}

Create a visually compelling comic panel sequence that captures this moment from the story. 
Show the characters, setting, and emotion clearly."""

        prompts.append({
            "panel_id": scene["scene_id"],
            "prompt": prompt,
            "negative_prompt": "blurry, low quality, distorted faces, bad anatomy"
        })
    
    return prompts


async def run_direct_pipeline(json_path: Path, output_dir: Path):
    """Run the direct pipeline without Gumloop."""
    
    print(f"\n{'='*60}")
    print("Direct Pipeline: Transcript -> Gemini (no Gumloop)")
    print(f"{'='*60}")
    
    # Load comic script
    print(f"\n[1/4] Loading comic script: {json_path.name}")
    with open(json_path) as f:
        comic_script = json.load(f)
    
    # Extract title
    title = "Story"
    for item in comic_script:
        if isinstance(item, dict) and item.get("_type") == "metadata":
            title = item.get("title") or item.get("source_file", "Story").replace(".mp3", "")
            break
    
    print(f"  Title: {title}")
    print(f"  Total items: {len(comic_script)}")
    
    # Extract scenes
    print(f"\n[2/4] Extracting story scenes...")
    scenes = extract_story_scenes(comic_script)
    print(f"  Extracted {len(scenes)} scenes")
    
    for scene in scenes:
        print(f"    Scene {scene['scene_id']}: {scene['text'][:60]}...")
    
    # Create prompts
    print(f"\n[3/4] Creating image prompts...")
    prompts = create_image_prompts(scenes, title)
    print(f"  Created {len(prompts)} prompts")
    
    # Generate images
    print(f"\n[4/4] Generating images with Gemini...")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    successful = 0
    failed = 0
    
    for prompt_data in prompts:
        panel_id = prompt_data["panel_id"]
        print(f"  Generating panel {panel_id}/{len(prompts)}...")
        
        result = await gemini_service.generate_panel(
            prompt=prompt_data["prompt"],
            panel_id=panel_id,
            style="storybook",
            negative_prompt=prompt_data.get("negative_prompt"),
            aspect_ratio="16:9",
            num_panels=4,
            temperature=0.3
        )
        
        if result.success and result.image_base64:
            # Save image
            image_path = output_dir / f"panel_{panel_id:03d}.png"
            gemini_service.save_image(result.image_base64, image_path)
            print(f"    [OK] Saved: {image_path.name}")
            successful += 1
        else:
            print(f"    [FAIL] Failed: {result.error_message}")
            failed += 1
        
        # Small delay between requests
        await asyncio.sleep(1)
    
    # Save metadata
    metadata = {
        "title": title,
        "generated_at": datetime.now().isoformat(),
        "total_scenes": len(scenes),
        "successful": successful,
        "failed": failed,
        "scenes": scenes,
        "prompts": prompts
    }
    
    metadata_path = output_dir / "metadata.json"
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)
    
    print(f"\n{'='*60}")
    print("Pipeline Complete!")
    print(f"  Successful: {successful}")
    print(f"  Failed: {failed}")
    print(f"  Output: {output_dir}")
    print(f"{'='*60}\n")
    
    # Open output directory
    import subprocess
    subprocess.run(["open", str(output_dir)])


def main():
    parser = argparse.ArgumentParser(description="Direct pipeline without Gumloop")
    parser.add_argument("json_file", help="Path to comicscript.json")
    parser.add_argument("-o", "--output", help="Output directory", default=None)
    args = parser.parse_args()
    
    json_path = Path(args.json_file)
    if not json_path.exists():
        # Try relative path
        json_path = Path(__file__).parent / args.json_file
    
    if not json_path.exists():
        print(f"File not found: {args.json_file}")
        sys.exit(1)
    
    if args.output:
        output_dir = Path(args.output)
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = Path(__file__).parent / "output" / f"direct_pipeline_{timestamp}"
    
    asyncio.run(run_direct_pipeline(json_path, output_dir))


if __name__ == "__main__":
    main()
