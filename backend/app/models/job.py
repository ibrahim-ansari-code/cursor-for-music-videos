"""
Job database model.
"""

from sqlalchemy import Column, String, Float, DateTime, JSON, Enum
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declarative_base
import enum

Base = declarative_base()


class JobStatus(enum.Enum):
    """Possible job statuses."""
    QUEUED = "queued"
    RUNNING = "running"
    GENERATING_SCENES = "generating_scenes"
    COMPOSING = "composing"
    DONE = "done"
    FAILED = "failed"


class Job(Base):
    """Job model for tracking video generation jobs."""
    
    __tablename__ = "jobs"
    
    job_id = Column(String(36), primary_key=True)
    status = Column(Enum(JobStatus), default=JobStatus.QUEUED, nullable=False)
    progress = Column(Float, default=0.0, nullable=False)
    message = Column(String(500), nullable=True)
    
    # Input URLs
    audio_url = Column(String(2048), nullable=False)
    image_url = Column(String(2048), nullable=False)
    
    # User configuration
    user_options = Column(JSON, nullable=True)
    
    # Audio metadata
    audio_duration_s = Column(Float, nullable=True)
    
    # Processed data
    segments_json = Column(JSON, nullable=True)
    scenes_json = Column(JSON, nullable=True)
    
    # Style outputs
    global_mood = Column(String(500), nullable=True)
    global_style = Column(String(500), nullable=True)
    
    # External service IDs
    gumloop_run_id = Column(String(100), nullable=True)
    
    # Final output
    final_video_url = Column(String(2048), nullable=True)
    
    # Error handling
    error = Column(String(2000), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
