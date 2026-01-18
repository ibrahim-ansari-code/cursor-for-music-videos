"""
Gumloop API service for AI scene generation.

Handles communication with Gumloop to generate scene prompts
based on audio transcription and theme image.
"""

import httpx
from typing import Optional

from app.config import get_settings


class GumloopService:
    """Service for interacting with Gumloop AI pipeline."""
    
    BASE_URL = "https://api.gumloop.com/api/v1"
    
    def __init__(self):
        settings = get_settings()
        if not settings.gumloop_api_key:
            raise ValueError("GUMLOOP_API_KEY not configured")
        
        self.api_key = settings.gumloop_api_key
        self.user_id = settings.gumloop_user_id
        self.pipeline_id = settings.gumloop_pipeline_id
        
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
    
    async def start_pipeline(
        self,
        image_url: str,
        transcript_clean: str,
        segments_json: list[dict],
        audio_duration_s: float,
        user_options: Optional[dict] = None,
    ) -> str:
        """
        Start a Gumloop pipeline run.
        
        Args:
            image_url: URL to the theme image
            transcript_clean: Cleaned transcript text
            segments_json: List of segment dictionaries with timing
            audio_duration_s: Total audio duration in seconds
            user_options: Optional user configuration
        
        Returns:
            Gumloop run ID
        """
        payload = {
            "user_id": self.user_id,
            "saved_item_id": self.pipeline_id,
            "pipeline_inputs": [
                {"input_name": "image_url", "value": image_url},
                {"input_name": "transcript_clean", "value": transcript_clean},
                {"input_name": "segments_json", "value": segments_json},
                {"input_name": "audio_duration_s", "value": audio_duration_s},
                {"input_name": "user_options", "value": user_options or {}},
            ],
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.BASE_URL}/start_pipeline",
                json=payload,
                headers=self.headers,
            )
            response.raise_for_status()
            data = response.json()
            return data["run_id"]
    
    async def get_pipeline_run(self, run_id: str) -> dict:
        """
        Get the status and outputs of a pipeline run.
        
        Args:
            run_id: Gumloop run ID
        
        Returns:
            Pipeline run data including status and outputs
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/get_pl_run",
                params={"run_id": run_id, "user_id": self.user_id},
                headers=self.headers,
            )
            response.raise_for_status()
            return response.json()
    
    async def wait_for_completion(
        self,
        run_id: str,
        poll_interval: float = 2.0,
        timeout: float = 300.0,
    ) -> dict:
        """
        Wait for a pipeline run to complete.
        
        Args:
            run_id: Gumloop run ID
            poll_interval: Seconds between status checks
            timeout: Maximum wait time in seconds
        
        Returns:
            Final pipeline run data with outputs
        """
        import asyncio
        
        elapsed = 0.0
        while elapsed < timeout:
            data = await self.get_pipeline_run(run_id)
            
            if data.get("state") == "DONE":
                return data
            elif data.get("state") == "FAILED":
                raise RuntimeError(f"Pipeline failed: {data.get('error')}")
            
            await asyncio.sleep(poll_interval)
            elapsed += poll_interval
        
        raise TimeoutError(f"Pipeline timed out after {timeout}s")
