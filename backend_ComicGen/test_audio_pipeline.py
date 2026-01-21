#!/usr/bin/env python3
"""
Test the full audio-to-images pipeline with any MP3 file.

This script:
1. Transcribes the audio using ElevenLabs
2. Sends transcript to Gumloop for prompt generation
3. Generates images using Gemini
4. Saves all outputs to a timestamped folder

Usage:
    python test_audio_pipeline.py <path_to_mp3>
    python test_audio_pipeline.py audio/my_song.mp3
    python test_audio_pipeline.py "/path/to/Santa's Day Off.mp3"
"""

import argparse
import asyncio
import sys
from pathlib import Path
from datetime import datetime

# Ensure we're using the venv
backend_dir = Path(__file__).parent / "backend"
venv_python = backend_dir / "venv" / "bin" / "python"

if venv_python.exists() and sys.executable != str(venv_python):
    # Re-run with the venv Python
    import subprocess
    result = subprocess.run([str(venv_python), __file__] + sys.argv[1:])
    sys.exit(result.returncode)

# Add backend to path
sys.path.insert(0, str(backend_dir))

from app.services.pipeline import pipeline_orchestrator, PipelineConfig


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Generate comic-style images from an MP3 audio file. Always uses comic style.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python test_audio_pipeline.py audio/my_song.mp3
    python test_audio_pipeline.py "/path/to/Santa's Day Off.mp3"
    python test_audio_pipeline.py --panels 8 audio/song.mp3
        """
    )
    parser.add_argument(
        "audio_file",
        type=str,
        help="Path to the MP3 file to process"
    )
    parser.add_argument(
        "--panels",
        type=int,
        default=6,
        help="Number of panels per page (default: 6)"
    )
    parser.add_argument(
        "--aspect-ratio",
        type=str,
        default="16:9",
        help="Aspect ratio for images (default: 16:9)"
    )
    parser.add_argument(
        "--keyterms",
        type=str,
        nargs="*",
        default=[],
        help="Key terms to help with transcription accuracy"
    )
    return parser.parse_args()


async def test_pipeline(args):
    """Run the full pipeline on the specified audio file."""
    
    # Configuration
    audio_file = Path(args.audio_file)
    
    # Handle relative paths
    if not audio_file.is_absolute():
        audio_file = Path(__file__).parent / audio_file
    
    if not audio_file.exists():
        print(f"Error: Audio file not found: {audio_file}")
        return
    
    print(f"Audio file: {audio_file.name}")
    print(f"Location: {audio_file}")
    
    # Create timestamped output directory using the audio file name
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = audio_file.stem.replace(" ", "_").replace("'", "")[:30]
    output_dir = Path(__file__).parent / "output" / f"{safe_name}_{timestamp}"
    
    # Pipeline configuration - always comic style
    config = PipelineConfig(
        output_dir=output_dir,
        image_style="comic",
        aspect_ratio=args.aspect_ratio,
        delay_between_images=1.0,
        save_images=True,
        save_metadata=True,
        num_panels=args.panels,
        temperature=0.2  # Low temperature for consistent, deterministic output
    )
    
    print(f"\nOutput directory: {output_dir}")
    print(f"Style: comic")
    print(f"Aspect ratio: {config.aspect_ratio}")
    print(f"Panels: {config.num_panels}")
    print("\n" + "="*60)
    
    # Run the pipeline
    try:
        result = await pipeline_orchestrator.run_from_audio(
            audio_path=audio_file,
            config=config,
            language="en",
            keyterms=args.keyterms if args.keyterms else None
        )
        
        # Display results
        print("\n" + "="*60)
        print("PIPELINE RESULTS")
        print("="*60)
        
        if result.success:
            print(f"SUCCESS!")
            print(f"\nStatistics:")
            print(f"   Total panels: {result.total_panels}")
            print(f"   Successful images: {result.successful_images}")
            print(f"   Failed images: {result.failed_images}")
            print(f"   Execution time: {result.execution_time_s:.1f}s")
            
            if result.gumloop_run_id:
                print(f"\nGumloop Run ID: {result.gumloop_run_id}")
            
            print(f"\nOutput directory: {result.output_dir}")
            print(f"\nGenerated files:")
            print(f"   - comicscript.json (transcript)")
            print(f"   - metadata.json (pipeline metadata)")
            print(f"   - panel_XXX.png (generated images)")
            
            # Show panel details
            if result.panels:
                print(f"\nPanel Details:")
                for panel in result.panels:
                    status_icon = "[OK]" if panel["status"] == "success" else "[FAIL]"
                    print(f"   {status_icon} Panel {panel['panel_id']}: {panel['prompt'][:60]}...")
                    if panel["status"] == "error":
                        print(f"      Error: {panel['error_message']}")
            
            # Open output directory
            print(f"\nOpening output directory...")
            import subprocess
            subprocess.run(["open", str(output_dir)])
            
        else:
            print(f"FAILED: {result.error_message}")
            
    except Exception as e:
        print(f"\nPipeline error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    args = parse_args()
    print("Audio-to-Images Pipeline")
    print("="*60)
    asyncio.run(test_pipeline(args))
