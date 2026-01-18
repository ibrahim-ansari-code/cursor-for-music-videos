# MeloVue Backend

FastAPI backend for the MeloVue AI music video generation service.

## Project Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py           # FastAPI application entry point
│   ├── config.py         # Configuration settings
│   ├── api/
│   │   ├── __init__.py
│   │   ├── uploads.py    # File upload endpoints
│   │   └── jobs.py       # Job management endpoints
│   ├── models/
│   │   ├── __init__.py
│   │   └── job.py        # Database models
│   ├── services/
│   │   ├── __init__.py
│   │   ├── transcription.py  # ElevenLabs STT service
│   │   ├── storage.py        # S3/R2 storage service
│   │   └── gumloop.py        # Gumloop AI pipeline service
│   └── worker/
│       ├── __init__.py
│       └── tasks.py      # Celery background tasks
├── requirements.txt
└── README.md
```

## Setup

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure environment variables:
Create a `.env` file with the following variables:
```
DATABASE_URL=sqlite:///./melovue.db
REDIS_URL=redis://localhost:6379/0
ELEVENLABS_API_KEY=your_key_here
GUMLOOP_API_KEY=your_key_here
GUMLOOP_USER_ID=your_user_id
GUMLOOP_PIPELINE_ID=your_pipeline_id
STORAGE_BUCKET=melovue-uploads
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
```

4. Run the development server:
```bash
uvicorn app.main:app --reload --port 8000
```

## API Endpoints

### Uploads
- `POST /uploads` - Upload audio and image files

### Jobs
- `POST /jobs` - Create a new video generation job
- `GET /jobs/{job_id}` - Get job status and progress

### Health
- `GET /` - Health check
- `GET /health` - Detailed health check

## Architecture

The backend follows the pipeline described in the main README:

1. **Upload** - Receive audio + image, validate, store in S3/R2
2. **Timing Prep** - Extract audio duration via ffprobe
3. **Transcription** - ElevenLabs STT for lyrics + timestamps
4. **Segmentation** - Build time-aligned segments
5. **Scene Generation** - Gumloop AI for scene prompts
6. **Video Generation** - Generate clips per scene
7. **Composition** - FFmpeg concat + audio mux
