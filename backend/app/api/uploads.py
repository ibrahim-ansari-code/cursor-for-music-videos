"""
Upload API endpoints.

Handles:
- POST /uploads - Upload audio and image files
"""

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from pydantic import BaseModel
from typing import Optional
import uuid

router = APIRouter()


class UploadResponse(BaseModel):
    """Response model for file uploads."""
    audio_upload_id: str
    image_upload_id: str
    audio_url: str
    image_url: str


@router.post("/", response_model=UploadResponse)
async def upload_files(
    audio: UploadFile = File(..., description="Audio file (mp3/wav/m4a)"),
    image: UploadFile = File(..., description="Theme image (png/jpg/webp)"),
    user_options: Optional[str] = Form(None, description="Optional JSON string with style options"),
):
    """
    Upload audio and image files for video generation.
    
    The files are validated and stored in object storage.
    Returns URLs that can be used to create a job.
    """
    # Validate audio file
    allowed_audio_types = ["audio/mpeg", "audio/mp3", "audio/wav", "audio/x-wav", "audio/m4a", "audio/mp4"]
    if audio.content_type not in allowed_audio_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid audio type: {audio.content_type}. Allowed: mp3, wav, m4a"
        )
    
    # Validate image file
    allowed_image_types = ["image/png", "image/jpeg", "image/jpg", "image/webp"]
    if image.content_type not in allowed_image_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid image type: {image.content_type}. Allowed: png, jpg, webp"
        )
    
    # Generate unique IDs
    audio_id = str(uuid.uuid4())
    image_id = str(uuid.uuid4())
    
    # TODO: Upload to object storage (S3/R2)
    # For now, return placeholder URLs
    audio_url = f"https://storage.example.com/audio/{audio_id}"
    image_url = f"https://storage.example.com/images/{image_id}"
    
    return UploadResponse(
        audio_upload_id=audio_id,
        image_upload_id=image_id,
        audio_url=audio_url,
        image_url=image_url,
    )
