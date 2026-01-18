# MeloVue - AI Music Video Generator

Transform your audio into stunning AI-generated music videos.

## Project Structure

```
cursor-for-music-videos/
├── frontend/                # Next.js frontend application
│   ├── app/                 # App router pages and layouts
│   ├── components/          # React components
│   ├── lib/                 # Utility functions
│   ├── public/              # Static assets
│   └── package.json
│
├── backend/                 # FastAPI backend service
│   ├── app/
│   │   ├── api/             # REST API endpoints
│   │   ├── models/          # Database models
│   │   ├── services/        # Business logic services
│   │   └── worker/          # Background job processing
│   └── requirements.txt
│
└── README.md
```

## Getting Started

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000)

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

API available at [http://localhost:8000](http://localhost:8000)

---

## System Architecture

### Core Invariants

**Invariant A — Audio is the source of truth for timing**
- `audio_duration_s` is canonical
- Every visual scene is a silent clip with duration summing to `audio_duration_s`
- Final exported MP4 has original MP3 muxed in and is trimmed/padded to exactly match `audio_duration_s`

**Invariant B — Frontend media is never forwarded directly**
- Frontend uploads once to backend
- Backend persists to object storage
- Everything downstream uses `audio_url` / `image_url` (signed URL or public URL)

---

## Pipeline Overview

### 1. Frontend Upload
- User selects `audio.mp3` and `theme_image.(png/jpg/webp)`
- Optional `user_options` (style tags, cut frequency, intensity, etc.)
- `POST /uploads` (multipart/form-data)
- Response: `{ audio_upload_id, image_upload_id, audio_url, image_url }`

### 2. Backend Validate + Persist
- Validate audio format, size, duration
- Validate image format, size
- Store in Object Storage (S3/R2)
- Create job: `POST /jobs { audio_url, image_url, user_options }`
- Response: `{ job_id }`

### 3. Frontend Progress Polling
- `GET /jobs/:job_id` (poll every 1–3s)
- Status: `queued | running | generating_scenes | composing | done | failed`

### 4. Worker Pipeline

**Step 1: Timing Prep**
- `ffprobe` for canonical duration
- Create segments template (fixed windows)

**Step 2: Transcription (ElevenLabs STT)**
- Extract lyrics + time alignment
- Handle instrumental/unclear vocals gracefully

**Step 3: Build Segments**
- `[{start_s, end_s, lyric_snippet, energy_hint}]`
- Ensure no gaps/overlaps, sum equals `audio_duration_s`

**Step 4: Gumloop AI Pipeline**
- Input: `image_url`, `transcript_clean`, `segments[]`, `audio_duration_s`
- Output: `global_mood`, `global_style`, `scenes[]`

**Step 5: Generate Video Clips**
- Per-scene video generation with style anchor
- Duration matches `end_s - start_s`

**Step 6: Compose Final Video**
- FFmpeg concat silent clips
- Mux original audio
- Trim/pad to exact `audio_duration_s`

### 5. Delivery
- Upload `final_video.mp4` to Object Storage
- Return `final_video_url` to frontend

---

## API Reference

### Upload Files
```
POST /uploads
Content-Type: multipart/form-data

Fields:
- audio (required): MP3/WAV/M4A file
- image (required): PNG/JPG/WebP file
- user_options (optional): JSON string

Response:
{
  "audio_upload_id": "uuid",
  "image_upload_id": "uuid",
  "audio_url": "signed_url",
  "image_url": "signed_url"
}
```

### Create Job
```
POST /jobs
Content-Type: application/json

Body:
{
  "audio_url": "string",
  "image_url": "string",
  "user_options": {}
}

Response:
{
  "job_id": "uuid"
}
```

### Get Job Status
```
GET /jobs/:job_id

Response:
{
  "job_id": "uuid",
  "status": "queued|running|generating_scenes|composing|done|failed",
  "progress": 0.0-1.0,
  "message": "human-readable",
  "final_video_url": "string|null",
  "global_mood": "string|null",
  "global_style": "string|null",
  "error": "string|null"
}
```

---

## Data Schemas

### Segment
```json
{
  "i": 0,
  "start_s": 0.0,
  "end_s": 4.0,
  "lyric_snippet": "...",
  "energy_hint": 0.42
}
```

### Scene
```json
{
  "i": 0,
  "start_s": 0.0,
  "end_s": 4.0,
  "prompt": "...",
  "camera": "...",
  "motion": "...",
  "negative_prompt": "..."
}
```

### Global Style Output
```json
{
  "global_mood": "...",
  "global_style": "...",
  "palette": ["..."],
  "motifs": ["..."],
  "do_not_include": ["..."]
}
```
