"""
Audio transcription service using ElevenLabs Speech-to-Text API.

This service transcribes audio files and outputs structured JSON with
lyric segments containing precise timing information.
"""

import os
from pathlib import Path
from typing import Optional

try:
    from elevenlabs.client import ElevenLabs
except ImportError:
    ElevenLabs = None

from app.config import get_settings


class TranscriptionService:
    """Service for transcribing audio files using ElevenLabs."""
    
    def __init__(self):
        settings = get_settings()
        if ElevenLabs is None:
            raise ImportError("elevenlabs package not installed")
        if not settings.elevenlabs_api_key:
            raise ValueError("ELEVENLABS_API_KEY not configured")
        self.client = ElevenLabs(api_key=settings.elevenlabs_api_key)
    
    def transcribe_audio(self, audio_path: Path, language: Optional[str] = None) -> dict:
        """
        Transcribe an audio file using ElevenLabs Speech-to-Text API.
        
        Args:
            audio_path: Path to the audio file
            language: Optional language code (ISO 639-1 or ISO 639-3)
        
        Returns:
            API response containing transcript and timing information
        """
        with open(audio_path, "rb") as audio_file:
            result = self.client.speech_to_text.convert(
                file=audio_file,
                model_id="scribe_v2"
            )
        return result
    
    def format_output(self, result, source_file: str) -> dict:
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
        
        # Extract words with timing
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
