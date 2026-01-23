"""
Audio transcription service using ElevenLabs Speech-to-Text API.

Transcribes audio files and outputs structured JSON with lyric segments
containing precise timing information for comic panel generation.
"""

import os
from pathlib import Path
from typing import Optional, List
from functools import lru_cache

from pydantic_settings import BaseSettings

try:
    from elevenlabs.client import ElevenLabs
except ImportError:
    ElevenLabs = None


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


class TranscriptionSettings(BaseSettings):
    """Transcription service settings from environment variables."""
    
    elevenlabs_api_key: Optional[str] = None
    
    model_config = {
        "env_file": _find_env_file(),
        "env_file_encoding": "utf-8",
        "extra": "ignore"
    }


@lru_cache()
def get_transcription_settings() -> TranscriptionSettings:
    """Get cached transcription settings instance."""
    return TranscriptionSettings()


# ============================================================================
# Transcription Service
# ============================================================================

class TranscriptionService:
    """Service for transcribing audio files using ElevenLabs."""
    
    def __init__(self):
        if ElevenLabs is None:
            raise ImportError(
                "elevenlabs package not installed. "
                "Run: pip install elevenlabs"
            )
        
        self.settings = get_transcription_settings()
        if not self.settings.elevenlabs_api_key:
            raise ValueError("ELEVENLABS_API_KEY not configured")
        
        self.client = ElevenLabs(api_key=self.settings.elevenlabs_api_key)
    
    def is_configured(self) -> bool:
        """Check if the transcription service is configured."""
        return self.settings.elevenlabs_api_key is not None
    
    def transcribe_audio(
        self,
        audio_path: Path,
        language: Optional[str] = None,
        keyterms: Optional[List[str]] = None
    ) -> dict:
        """
        Transcribe an audio file using ElevenLabs Speech-to-Text API.
        
        Args:
            audio_path: Path to the audio file
            language: Optional language code (ISO 639-1 or ISO 639-3)
            keyterms: Optional list of character names/terms to improve recognition
        
        Returns:
            API response containing transcript and timing information
        """
        with open(audio_path, "rb") as audio_file:
            # Build API call parameters
            params = {
                "file": audio_file,
                "model_id": "scribe_v2"
            }
            
            if language:
                params["language_code"] = language
            
            result = self.client.speech_to_text.convert(**params)
        
        return result
    
    def format_comic_script(self, result, source_file: str) -> dict:
        """
        Format the API response into comic script format.
        
        Args:
            result: ElevenLabs API response object
            source_file: Name of the source audio file
        
        Returns:
            Formatted dictionary with segments and metadata
        """
        # Extract segments with timing
        segments = []
        if hasattr(result, 'words') and result.words:
            # Group words into natural segments (by sentence/phrase)
            current_segment = {
                "start_s": 0.0,
                "end_s": 0.0,
                "lyric_snippet": "",
                "words": []
            }
            
            for word in result.words:
                word_text = word.text if hasattr(word, 'text') else str(word)
                word_start = float(word.start) if hasattr(word, 'start') else 0.0
                word_end = float(word.end) if hasattr(word, 'end') else 0.0
                
                if not current_segment["words"]:
                    current_segment["start_s"] = word_start
                
                current_segment["words"].append(word_text)
                current_segment["end_s"] = word_end
                
                # Create segment break on punctuation or every ~10 words
                if (word_text.rstrip().endswith(('.', '!', '?', ',')) or 
                    len(current_segment["words"]) >= 10):
                    current_segment["lyric_snippet"] = " ".join(current_segment["words"])
                    segments.append({
                        "start_s": current_segment["start_s"],
                        "end_s": current_segment["end_s"],
                        "lyric_snippet": current_segment["lyric_snippet"]
                    })
                    current_segment = {
                        "start_s": 0.0,
                        "end_s": 0.0,
                        "lyric_snippet": "",
                        "words": []
                    }
            
            # Don't forget the last segment
            if current_segment["words"]:
                current_segment["lyric_snippet"] = " ".join(current_segment["words"])
                segments.append({
                    "start_s": current_segment["start_s"],
                    "end_s": current_segment["end_s"],
                    "lyric_snippet": current_segment["lyric_snippet"]
                })
        
        # If no word-level timing, use segment-level
        elif hasattr(result, 'segments') and result.segments:
            for seg in result.segments:
                segments.append({
                    "start_s": float(seg.start) if hasattr(seg, 'start') else 0.0,
                    "end_s": float(seg.end) if hasattr(seg, 'end') else 0.0,
                    "lyric_snippet": seg.text if hasattr(seg, 'text') else ""
                })
        
        # Build output
        full_text = result.text if hasattr(result, 'text') else ""
        duration = float(result.duration) if hasattr(result, 'duration') else 0.0
        language = result.language if hasattr(result, 'language') else "unknown"
        
        return {
            "metadata": {
                "source_file": source_file,
                "duration_s": duration,
                "language": language,
                "total_segments": len(segments)
            },
            "full_transcript": full_text,
            "segments": segments
        }
