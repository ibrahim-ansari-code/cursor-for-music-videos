#!/usr/bin/env python3
"""
MP3 Transcription Tool using ElevenLabs Speech-to-Text API

This script transcribes MP3 audio files and outputs structured JSON with
lyric segments containing precise timing information.

Usage:
    python3 transcribe_mp3.py "song.mp3"  (outputs to segments.json)
    python3 transcribe_mp3.py "song.mp3" --output "custom_output.json"
    python3 transcribe_mp3.py "song.mp3" --language en
"""

import argparse
import json
import os
import sys
from pathlib import Path

try:
    from elevenlabs.client import ElevenLabs
except ImportError:
    print("Error: elevenlabs package not installed.")
    print("Run: pip install elevenlabs python-dotenv")
    sys.exit(1)

try:
    from dotenv import load_dotenv
except ImportError:
    # dotenv is optional - environment variables can be set directly
    load_dotenv = None


def load_environment():
    """Load environment variables from .env file if available."""
    if load_dotenv:
        # Look for .env in the script's directory
        script_dir = Path(__file__).parent
        env_path = script_dir / ".env"
        if env_path.exists():
            load_dotenv(env_path)


def get_api_key():
    """Get the ElevenLabs API key from environment variables."""
    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        print("Error: ELEVENLABS_API_KEY environment variable not set.")
        print("Set it in your .env file or export it directly:")
        print("  export ELEVENLABS_API_KEY='your_api_key_here'")
        sys.exit(1)
    return api_key


def transcribe_audio(client: ElevenLabs, audio_path: Path, language: str = None) -> dict:
    """
    Transcribe an audio file using ElevenLabs Speech-to-Text API.
    
    Args:
        client: ElevenLabs client instance
        audio_path: Path to the audio file
        language: Optional language code (ISO 639-1 or ISO 639-3)
    
    Returns:
        API response containing transcript and timing information
    """
    print(f"Transcribing: {audio_path.name}")
    print("This may take a moment...")
    
    with open(audio_path, "rb") as audio_file:
        # Use the convert endpoint which provides segments and words with timing
        # model_id is required by the ElevenLabs API
        result = client.speech_to_text.convert(
            file=audio_file,
            model_id="scribe_v2"  # Latest ElevenLabs speech-to-text model
        )
    
    return result


def format_output(result, source_file: str) -> dict:
    """
    Format the API response into the required output structure.
    
    Args:
        result: ElevenLabs API response object
        source_file: Name of the source audio file
    
    Returns:
        Formatted dictionary matching the required output schema
    """
    # Extract segments with timing
    segments = []
    if hasattr(result, 'segments') and result.segments:
        for seg in result.segments:
            segments.append({
                "start_s": float(seg.start) if hasattr(seg, 'start') else 0.0,
                "end_s": float(seg.end) if hasattr(seg, 'end') else 0.0,
                "lyric_snippet": seg.text if hasattr(seg, 'text') else ""
            })
    
    # Extract words with timing (useful for precise sync)
    words = []
    if hasattr(result, 'words') and result.words:
        for word in result.words:
            words.append({
                "start_s": float(word.start) if hasattr(word, 'start') else 0.0,
                "end_s": float(word.end) if hasattr(word, 'end') else 0.0,
                "word": word.text if hasattr(word, 'text') else ""
            })
    
    # Build the output structure
    output = {
        "source_file": source_file,
        "transcription": {
            "text": result.text if hasattr(result, 'text') else "",
            "language_code": result.language if hasattr(result, 'language') else "unknown",
            "duration": float(result.duration) if hasattr(result, 'duration') else 0.0
        },
        "segments": segments,
        "words": words
    }
    
    return output


def save_json(data: dict, output_path: Path):
    """Save data to a JSON file with pretty formatting."""
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"Output saved to: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Transcribe MP3 files using ElevenLabs Speech-to-Text API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 transcribe_mp3.py "song.mp3"                      # outputs to segments.json
  python3 transcribe_mp3.py "song.mp3" --output "output.json"
  python3 transcribe_mp3.py "song.mp3" --language en
        """
    )
    
    parser.add_argument(
        "audio_file",
        type=str,
        help="Path to the MP3 audio file to transcribe"
    )
    
    parser.add_argument(
        "--output", "-o",
        type=str,
        default=None,
        help="Output JSON file path (default: segments.json)"
    )
    
    parser.add_argument(
        "--language", "-l",
        type=str,
        default=None,
        help="Language code hint (ISO 639-1/639-3, e.g., 'en', 'eng')"
    )
    
    args = parser.parse_args()
    
    # Load environment variables
    load_environment()
    
    # Validate input file
    audio_path = Path(args.audio_file)
    if not audio_path.exists():
        print(f"Error: File not found: {audio_path}")
        sys.exit(1)
    
    if not audio_path.suffix.lower() in ['.mp3', '.wav', '.m4a', '.ogg', '.flac']:
        print(f"Warning: Unexpected file extension '{audio_path.suffix}'. Proceeding anyway...")
    
    # Determine output path
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = Path("segments.json")
    
    # Get API key and create client
    api_key = get_api_key()
    client = ElevenLabs(api_key=api_key)
    
    try:
        # Transcribe the audio
        result = transcribe_audio(client, audio_path, args.language)
        
        # Format the output
        output_data = format_output(result, audio_path.name)
        
        # Display summary
        print(f"\nTranscription complete!")
        print(f"  Duration: {output_data['transcription']['duration']:.2f} seconds")
        print(f"  Language: {output_data['transcription']['language_code']}")
        print(f"  Segments: {len(output_data['segments'])}")
        print(f"  Words: {len(output_data['words'])}")
        
        # Save to JSON
        save_json(output_data, output_path)
        
        # Print first few segments as preview
        if output_data['segments']:
            print(f"\nFirst segment preview:")
            seg = output_data['segments'][0]
            print(f"  [{seg['start_s']:.2f}s - {seg['end_s']:.2f}s] {seg['lyric_snippet'][:80]}...")
        
    except Exception as e:
        print(f"Error during transcription: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
