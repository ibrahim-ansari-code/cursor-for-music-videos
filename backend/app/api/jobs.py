"""
Jobs API endpoints.

Handles:
- POST /jobs - Create a new video generation job
- GET /jobs/:job_id - Get job status and progress
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from enum import Enum
import uuid

router = APIRouter()


class JobStatus(str, Enum):
    """Possible job statuses."""
    QUEUED = "queued"
    RUNNING = "running"
    GENERATING_SCENES = "generating_scenes"
    COMPOSING = "composing"
    DONE = "done"
    FAILED = "failed"


class CreateJobRequest(BaseModel):
    """Request model for creating a job."""
    audio_url: str
    image_url: str
    user_options: Optional[dict] = None


class CreateJobResponse(BaseModel):
    """Response model for job creation."""
    job_id: str


class JobStatusResponse(BaseModel):
    """Response model for job status."""
    job_id: str
    status: JobStatus
    progress: float
    message: Optional[str] = None
    final_video_url: Optional[str] = None
    global_mood: Optional[str] = None
    global_style: Optional[str] = None
    error: Optional[str] = None


# In-memory job storage (replace with database in production)
jobs_db: dict[str, dict] = {}


@router.post("/", response_model=CreateJobResponse)
async def create_job(request: CreateJobRequest):
    """
    Create a new video generation job.
    
    The job is queued for processing by the worker.
    """
    job_id = str(uuid.uuid4())
    
    # Store job in database
    jobs_db[job_id] = {
        "job_id": job_id,
        "status": JobStatus.QUEUED,
        "progress": 0.0,
        "message": "Job queued for processing",
        "audio_url": request.audio_url,
        "image_url": request.image_url,
        "user_options": request.user_options,
        "final_video_url": None,
        "global_mood": None,
        "global_style": None,
        "error": None,
    }
    
    # TODO: Enqueue job for worker processing
    # celery_app.send_task('worker.process_job', args=[job_id])
    
    return CreateJobResponse(job_id=job_id)


@router.get("/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    """
    Get the status and progress of a job.
    
    Poll this endpoint to track video generation progress.
    """
    if job_id not in jobs_db:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = jobs_db[job_id]
    
    return JobStatusResponse(
        job_id=job["job_id"],
        status=job["status"],
        progress=job["progress"],
        message=job["message"],
        final_video_url=job["final_video_url"],
        global_mood=job["global_mood"],
        global_style=job["global_style"],
        error=job["error"],
    )
