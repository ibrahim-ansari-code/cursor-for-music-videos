"""
FastAPI service for rendering audio panels from Gumloop JSON.

Endpoints:
- POST /render_panel: Accept Gumloop JSON, generate audio
- GET /audio/{audio_id}.mp3: Serve generated audio files
"""

import os
import uuid
import time
from pathlib import Path
from typing import Dict, List, Optional
import hashlib
import asyncio
import re
from concurrent.futures import ThreadPoolExecutor

from fastapi import FastAPI, HTTPException, Request, UploadFile, File, Form, Query
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from dotenv import load_dotenv
import shutil
import tempfile

from db import VoiceCache
from elevenlabs_client import ElevenLabsClient
from audio import load_audio_from_bytes, stitch_audio_clips, export_mp3
import json


# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(title="Gumloop Audio Renderer", version="1.0.0")

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize components
db = VoiceCache(db_path=os.getenv("DATABASE_PATH", "./voice_cache.db"))
elevenlabs = ElevenLabsClient()

# Output directory
OUTPUT_BASE_DIR = Path(os.getenv("OUTPUT_BASE_DIR", "./out"))

# Narrator voice ID
NARRATOR_VOICE_ID = os.getenv("NARRATOR_VOICE_ID")
if not NARRATOR_VOICE_ID:
    print("No NARRATOR_VOICE_ID provided, selecting default narrator voice...")
    try:
        narrator_requirements = {
            "voice_gender": "neutral",
            "age_range": "adult",
            "timbre": "clear",
            "pacing": "normal",
            "energy": "medium",
            "accent_preference": "none"
        }
        NARRATOR_VOICE_ID = elevenlabs.select_voice_id(narrator_requirements)
        print(f"Selected narrator voice ID: {NARRATOR_VOICE_ID}")
    except Exception as e:
        NARRATOR_VOICE_ID = "cgSgspJ2msm6clMCkdW9"
        print(f"Using fallback narrator voice ID: {NARRATOR_VOICE_ID}")


# Pydantic models for request/response
class VoiceRequirements(BaseModel):
    """Voice requirements for character."""
    voice_gender: str = Field(..., description="male|female|neutral")
    age_range: str = Field(..., description="child|teen|adult|elderly")
    pitch: str = Field(..., description="low|medium|high")
    pacing: str = Field(..., description="slow|normal|fast")
    energy: str = Field(..., description="low|medium|high")
    timbre: str = Field(..., description="warm|gravelly|clear|breathy|etc")
    accent_preference: str = Field(default="none", description="none or accent name")


class CharacterRegistry(BaseModel):
    """Character registry entry."""
    character_id: str
    name_or_label: str
    voice_requirements: VoiceRequirements


class ScriptLine(BaseModel):
    """Script line with speaker and text."""
    speaker: str = Field(..., description="Narrator or character_id")
    text: str
    emotion: str = Field(default="", description="Short phrase")
    intensity_1_to_10: int = Field(default=0, ge=0, le=10)
    pause_ms_after: int = Field(default=350, ge=0)


class RenderPanelRequest(BaseModel):
    """Request model for /render_panel endpoint."""
    character_registry: List[CharacterRegistry] = Field(default_factory=list)
    script_lines: List[ScriptLine]


class RenderPanelResponse(BaseModel):
    """Response model for /render_panel endpoint."""
    audio_id: str
    status: str
    message: str
    audio_url: Optional[str] = None


def clone_voice_if_reference_available(character_id: str, reference_audio_paths: List[str]) -> Optional[str]:
    if not reference_audio_paths:
        return None
    try:
        for path in reference_audio_paths:
            if not Path(path).exists():
                return None
        voice_id = elevenlabs.clone_voice(
            name=f"Cloned Voice - {character_id}",
            audio_files=reference_audio_paths,
            description=f"Voice clone for character {character_id}"
        )
        print(f"Successfully cloned voice for {character_id}: {voice_id}")
        return voice_id
    except Exception as e:
        print(f"Error cloning voice for {character_id}: {e}")
        return None


def get_voice_id_for_character(character_id: str, character_registry: List[CharacterRegistry], reference_audio_paths: Optional[List[str]] = None) -> str:
    cached_voice_id = db.get_voice_id("default_book", character_id)
    if cached_voice_id:
        return cached_voice_id
    if reference_audio_paths:
        cloned_voice_id = clone_voice_if_reference_available(character_id, reference_audio_paths)
        if cloned_voice_id:
            db.set_voice_id("default_book", character_id, cloned_voice_id)
            return cloned_voice_id
    character = next((c for c in character_registry if c.character_id == character_id), None)
    if not character:
        raise ValueError(f"Character {character_id} not found in registry")
    voice_requirements_dict = character.voice_requirements.model_dump()
    voice_id = elevenlabs.select_voice_id(voice_requirements_dict)
    db.set_voice_id("default_book", character_id, voice_id)
    return voice_id


def extract_json_from_text(text: str) -> dict | list | None:
    text = text.strip()
    
    if not text:
        return None
    
    if text.startswith('[') and text.endswith(']'):
        try:
            return json.loads(text)
        except:
            pass
    
    if text.startswith('{') and text.endswith('}'):
        try:
            return json.loads(text)
        except:
            pass
    
    json_match = re.search(r'\[[\s\S]*\]', text)
    if json_match:
        try:
            return json.loads(json_match.group(0))
        except:
            pass
    
    json_match = re.search(r'\{[\s\S]*\}', text)
    if json_match:
        try:
            return json.loads(json_match.group(0))
        except:
            pass
    
    lines = text.split('\n')
    for line in lines:
        line = line.strip()
        if line.startswith('[') or line.startswith('{'):
            try:
                return json.loads(line)
            except:
                continue
    
    return None


def normalize_payload(payload) -> dict:
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON string: {e}")
    
    if isinstance(payload, list):
        payload = {"script_lines": payload}
    
    if not isinstance(payload, dict):
        raise ValueError(f"Payload must be dict, list, or JSON string, got {type(payload)}")
    
    if "response" in payload:
        if isinstance(payload["response"], list):
            payload["script_lines"] = payload["response"]
        elif isinstance(payload["response"], str):
            try:
                parsed = json.loads(payload["response"])
                if isinstance(parsed, list):
                    payload["script_lines"] = parsed
                elif isinstance(parsed, dict):
                    payload.update(parsed)
            except:
                pass
    
    if "text" in payload:
        if isinstance(payload["text"], list):
            payload["script_lines"] = payload["text"]
        elif isinstance(payload["text"], str):
            try:
                parsed = json.loads(payload["text"])
                if isinstance(parsed, list):
                    payload["script_lines"] = parsed
                elif isinstance(parsed, dict):
                    payload.update(parsed)
            except:
                pass
    
    unwrapped = payload
    max_depth = 10
    depth = 0
    
    while depth < max_depth:
        if "output" in unwrapped and isinstance(unwrapped["output"], dict):
            unwrapped = unwrapped["output"]
            depth += 1
            continue
        elif "outputs" in unwrapped and isinstance(unwrapped["outputs"], dict):
            if "output" in unwrapped["outputs"]:
                unwrapped = unwrapped["outputs"]["output"]
            else:
                unwrapped = unwrapped["outputs"]
            depth += 1
            continue
        elif "data" in unwrapped and isinstance(unwrapped["data"], dict):
            unwrapped = unwrapped["data"]
            depth += 1
            continue
        elif "result" in unwrapped and isinstance(unwrapped["result"], dict):
            unwrapped = unwrapped["result"]
            depth += 1
            continue
        else:
            if all(key in unwrapped for key in ["script_lines"]):
                break
            depth += 1
            if depth >= max_depth:
                break
    
    normalized = unwrapped.copy()
    
    if "script_lines" not in normalized:
        raise ValueError("Payload must contain 'script_lines' field")
    
    if not isinstance(normalized["script_lines"], list):
        raise ValueError("'script_lines' must be a list")
    
    if "character_registry" not in normalized or not normalized["character_registry"]:
        speakers = set()
        for line in normalized["script_lines"]:
            speaker = line.get("speaker", "")
            if speaker and speaker.lower() != "narrator":
                speakers.add(speaker)
        
        character_registry = []
        for speaker in sorted(speakers):
            character_registry.append({
                "character_id": speaker,
                "name_or_label": speaker,
                "voice_requirements": {
                    "voice_gender": "neutral",
                    "age_range": "adult",
                    "pitch": "medium",
                    "pacing": "normal",
                    "energy": "medium",
                    "timbre": "clear",
                    "accent_preference": "none"
                }
            })
        
        normalized["character_registry"] = character_registry
        print(f"Built character_registry from script_lines: {len(character_registry)} characters")
    
    if not isinstance(normalized["character_registry"], list):
        normalized["character_registry"] = []
    for i, line in enumerate(normalized["script_lines"]):
        if not isinstance(line, dict):
            raise ValueError(f"script_lines[{i}] must be a dict")
        if "speaker" not in line:
            raise ValueError(f"script_lines[{i}] missing 'speaker' field")
        if "text" not in line:
            raise ValueError(f"script_lines[{i}] missing 'text' field")
    
    return normalized


def format_text_with_emotion(text: str, emotion: str, intensity: int) -> str:
    # Don't add emotion cues - ElevenLabs handles emotion naturally
    # The emotion and intensity are metadata for voice selection, not text to speak
    return text


def generate_audio_id(script_lines: List) -> str:
    script_content = json.dumps([line.model_dump() if hasattr(line, 'model_dump') else line for line in script_lines], sort_keys=True)
    return hashlib.md5(script_content.encode()).hexdigest()[:16]


def generate_tts_for_line(line, character_registry: List, narrator_voice_id: str) -> tuple:
    if line.speaker.lower() == "narrator":
        voice_id = narrator_voice_id
    else:
        voice_id = get_voice_id_for_character(
            line.speaker,
            character_registry,
            reference_audio_paths=None
        )
    formatted_text = format_text_with_emotion(line.text, line.emotion, line.intensity_1_to_10)
    print(f"Generating TTS for {line.speaker}: {line.text[:50]}...")
    audio_bytes = elevenlabs.text_to_speech(text=formatted_text, voice_id=voice_id)
    audio_segment = load_audio_from_bytes(audio_bytes)
    return audio_segment, line.pause_ms_after


@app.post("/render_panel", response_model=RenderPanelResponse)
async def render_panel(request: Request, run_id: Optional[str] = Query(None)):
    try:
        query_params = dict(request.query_params)
        
        if not run_id:
            run_id = query_params.get("run_id")
        
        if run_id:
            if run_id.startswith("{{") and run_id.endswith("}}"):
                run_id = None
            elif run_id.startswith("{") and run_id.endswith("}") and "run_id" in run_id.lower():
                run_id = None
        
        content_type = request.headers.get("content-type", "").lower()
        body = await request.body()
        
        if "application/json" in content_type:
            try:
                raw_payload = await request.json()
            except Exception as e:
                body_text = body.decode('utf-8')
                raw_payload = extract_json_from_text(body_text)
                if not raw_payload:
                    raise HTTPException(status_code=400, detail=f"Invalid JSON: {str(e)}")
        else:
            body_text = body.decode('utf-8')
            
            raw_payload = extract_json_from_text(body_text)
            if not raw_payload:
                raise HTTPException(status_code=400, detail=f"Could not extract JSON array from text payload. First 500 chars: {body_text[:500]}")
        
        
        normalized_payload = normalize_payload(raw_payload)
        
        if not run_id:
            if isinstance(normalized_payload, dict):
                run_id = normalized_payload.get("run_id")
            if not run_id and isinstance(raw_payload, dict):
                run_id = raw_payload.get("run_id")
        
        print(f"script_lines count: {len(normalized_payload.get('script_lines', []))}")
        
        request_data = RenderPanelRequest(**normalized_payload)
        script_id = generate_audio_id(request_data.script_lines)
        audio_id = f"{script_id}_{run_id[:8]}" if run_id else script_id
        
        output_dir = OUTPUT_BASE_DIR
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{audio_id}.mp3"
        if output_path.exists():
            audio_url = f"/audio/{audio_id}.mp3"
            return RenderPanelResponse(
                audio_id=audio_id,
                status="success",
                message="Audio already exists",
                audio_url=audio_url
            )
        
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [
                loop.run_in_executor(
                    executor,
                    generate_tts_for_line,
                    line,
                    request_data.character_registry,
                    NARRATOR_VOICE_ID
                )
                for line in request_data.script_lines
            ]
            results = await asyncio.gather(*futures)
        
        audio_clips = [result[0] for result in results]
        pauses_ms = [result[1] for result in results]
        
        final_audio = stitch_audio_clips(audio_clips, pauses_ms)
        export_mp3(final_audio, output_path)
        
        audio_url = f"/audio/{audio_id}.mp3"
        
        return RenderPanelResponse(
            audio_id=audio_id,
            status="success",
            message=f"Audio generated successfully",
            audio_url=audio_url
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error rendering panel: {str(e)}")


@app.get("/audio/{audio_id}.mp3")
async def get_audio(audio_id: str, request: Request):
    # Check flat structure first (new files)
    audio_file = OUTPUT_BASE_DIR / f"{audio_id}.mp3"
    if audio_file.exists():
        return FileResponse(
            str(audio_file),
            media_type="audio/mpeg",
            filename=f"{audio_id}.mp3"
        )
    
    # Check nested structure (old files)
    for book_dir in OUTPUT_BASE_DIR.iterdir():
        if not book_dir.is_dir():
            continue
        for chapter_dir in book_dir.iterdir():
            if not chapter_dir.is_dir():
                continue
            for panel_dir in chapter_dir.iterdir():
                if not panel_dir.is_dir():
                    continue
                audio_file = panel_dir / f"{audio_id}.mp3"
                if audio_file.exists():
                    return FileResponse(
                        str(audio_file),
                        media_type="audio/mpeg",
                        filename=f"{audio_id}.mp3"
                    )
    
    raise HTTPException(status_code=404, detail=f"Audio file {audio_id}.mp3 not found")


@app.post("/render_from_url")
async def render_from_url(image_url: str = Form(...)):
    import requests as req_lib
    import time
    
    try:
        gumloop_url = "https://api.gumloop.com/api/v1/start_pipeline"
        gumloop_params = {
            "api_key": "c2a2b3e665814a929b521788d5b4fd4f",
            "user_id": "o55HMJKqN5Us2Bv8k4hDVTPM2kh1",
            "saved_item_id": "6aAzik174E3Zr7SH7xvjPC"
        }
        gumloop_headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        # Add cache-busting parameter to prevent vision model caching
        # This forces the Analyze Image node to treat each request as a new image
        # Remove any existing timestamp parameter
        image_url_clean = re.sub(r'[?&]t=\d+', '', image_url)
        # Add fresh timestamp
        separator = "&" if "?" in image_url_clean else "?"
        cache_busted_url = f"{image_url_clean}{separator}t={int(time.time() * 1000)}"
        
        payload = {"image_url": cache_busted_url}
        
        gumloop_response = req_lib.post(
            gumloop_url,
            json=payload,
            headers=gumloop_headers,
            params=gumloop_params,
            timeout=120
        )
        
        if gumloop_response.status_code != 200:
            error_text = gumloop_response.text
            try:
                error_json = gumloop_response.json()
            except:
                pass
            raise HTTPException(status_code=gumloop_response.status_code, detail=f"Gumloop API error: {error_text}")
        
        gumloop_json = gumloop_response.json()
        
        run_id = gumloop_json.get("run_id")
        if not run_id:
            raise HTTPException(status_code=500, detail="Gumloop response missing run_id")
        
        
        return RenderPanelResponse(
            audio_id="pending",
            status="pending",
            message=f"Processing...",
            audio_url=None
        )
    
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        if "500" in error_msg or "Internal Server Error" in error_msg:
            raise HTTPException(
                status_code=500,
                detail=f"Gumloop API error: {error_msg}. Possible causes: 1) Invalid API key/user_id/saved_item_id, 2) Pipeline not configured correctly, 3) Gumloop service issue. Please verify your Gumloop credentials and pipeline configuration."
            )
        raise HTTPException(status_code=500, detail=f"Error processing image: {error_msg}")


@app.get("/audio/recent")
async def get_recent_audio(limit: int = 10):
    """Get list of recently generated audio files."""
    try:
        audio_files = []
        output_dir = OUTPUT_BASE_DIR
        
        # Get all MP3 files, sorted by modification time
        mp3_files = sorted(
            output_dir.glob("*.mp3"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )[:limit]
        
        for audio_file in mp3_files:
            audio_id = audio_file.stem
            audio_files.append({
                "audio_id": audio_id,
                "audio_url": f"/audio/{audio_id}.mp3",
                "size_bytes": audio_file.stat().st_size,
                "modified_time": audio_file.stat().st_mtime
            })
        
        return {"audio_files": audio_files}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing audio: {str(e)}")


@app.get("/audio/poll")
async def poll_audio_status(image_url: str):
    """Poll for audio completion. Returns audio if ready, pending if not."""
    try:
        
        # Check recent audio files (last 5)
        output_dir = OUTPUT_BASE_DIR
        mp3_files = sorted(
            output_dir.glob("*.mp3"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )[:5]
        
        # Return most recent if it exists and was created recently (within last 2 minutes)
        if mp3_files:
            latest = mp3_files[0]
            age_seconds = time.time() - latest.stat().st_mtime
            if age_seconds < 120:  # Created within last 2 minutes
                audio_id = latest.stem
                return {
                    "status": "ready",
                    "audio_id": audio_id,
                    "audio_url": f"/audio/{audio_id}.mp3"
                }
        
        return {"status": "pending", "audio_id": None, "audio_url": None}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error polling audio: {str(e)}")


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "gumloop-audio-renderer"}


@app.get("/")
async def root():
    return {
        "service": "Gumloop Audio Renderer",
        "version": "1.0.0",
        "endpoints": {
            "POST /render_panel": "Render audio panel from Gumloop JSON",
            "POST /upload_and_render": "Upload image file and render audio",
            "GET /audio/{audio_id}.mp3": "Serve generated audio file",
            "GET /health": "Health check"
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
