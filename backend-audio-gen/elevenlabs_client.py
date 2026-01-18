import os
import time
import requests
from typing import Dict, Optional


class ElevenLabsClient:
    def __init__(self):
        self.api_key = os.getenv("ELEVENLABS_API_KEY")
        if not self.api_key:
            raise ValueError("ELEVENLABS_API_KEY environment variable is required")
        self.base_url = os.getenv("ELEVENLABS_BASE_URL", "https://api.elevenlabs.io")
        self.model_id = "eleven_multilingual_v2"
    
    def list_voices(self) -> list:
        url = f"{self.base_url}/v1/voices"
        headers = {"xi-api-key": self.api_key}
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        return data.get("voices", [])
    
    def search_voices(self, search: str = "", page_size: int = 20) -> list:
        all_voices = self.list_voices()
        if not search:
            return all_voices[:page_size]
        search_lower = search.lower()
        filtered = [
            v for v in all_voices
            if search_lower in v.get("name", "").lower() or
               search_lower in v.get("description", "").lower() or
               search_lower in str(v.get("labels", {})).lower()
        ]
        return filtered[:page_size] if filtered else all_voices[:page_size]
    
    def select_voice_id(self, voice_requirements: Dict) -> str:
        query_parts = []
        
        gender = voice_requirements.get("voice_gender", "neutral")
        age = voice_requirements.get("age_range", "adult")
        timbre = voice_requirements.get("timbre", "clear")
        pacing = voice_requirements.get("pacing", "normal")
        energy = voice_requirements.get("energy", "medium")
        accent = voice_requirements.get("accent_preference", "none")
        
        if gender != "neutral":
            query_parts.append(gender)
        if age:
            query_parts.append(age)
        if timbre:
            query_parts.append(timbre)
        if pacing == "slow":
            query_parts.append("calm")
        elif pacing == "fast" or energy == "high":
            query_parts.append("energetic")
        
        if accent != "none":
            query_parts.append(accent)
        
        search_query = " ".join(query_parts) if query_parts else "narration"
        
        voices = self.search_voices(search=search_query, page_size=20)
        
        if not voices:
            voices = self.search_voices(search="narration", page_size=20)
        
        if not voices:
            raise ValueError("No voices found")
        
        best_voice = voices[0]
        return best_voice["voice_id"]
    
    def text_to_speech(self, text: str, voice_id: str, model_id: Optional[str] = None, max_retries: int = 3) -> bytes:
        url = f"{self.base_url}/v1/text-to-speech/{voice_id}"
        headers = {
            "xi-api-key": self.api_key,
            "Content-Type": "application/json"
        }
        data = {
            "text": text,
            "model_id": model_id or self.model_id,
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75,
                "style": 0.0,
                "use_speaker_boost": True
            }
        }
        
        for attempt in range(max_retries):
            response = requests.post(url, json=data, headers=headers)
            
            if response.status_code == 429:
                # Rate limited - wait with exponential backoff
                wait_time = (2 ** attempt) + (attempt * 0.5)  # 1s, 2.5s, 5s, etc.
                if attempt < max_retries - 1:
                    print(f"Rate limited (429). Waiting {wait_time:.1f}s before retry {attempt + 1}/{max_retries}...")
                    time.sleep(wait_time)
                    continue
                else:
                    response.raise_for_status()
            else:
                response.raise_for_status()
                return response.content
        
        response.raise_for_status()
        return response.content
    
    def clone_voice(self, name: str, files: list[str]) -> str:
        url = f"{self.base_url}/v1/voices/add"
        headers = {"xi-api-key": self.api_key}
        
        files_data = []
        for file_path in files:
            with open(file_path, "rb") as f:
                files_data.append(("files", (os.path.basename(file_path), f.read(), "audio/mpeg")))
        
        data = {"name": name}
        response = requests.post(url, headers=headers, data=data, files=files_data)
        response.raise_for_status()
        result = response.json()
        return result["voice_id"]
