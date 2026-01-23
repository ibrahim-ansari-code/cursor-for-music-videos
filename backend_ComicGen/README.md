# MeloVue Backend - Comic Generation API

AI-powered audio to comic panel generation using ElevenLabs, Claude, and Gemini.

## Architecture

```
Audio File → ElevenLabs (Transcription) → Claude (Prompt Generation) → Gemini (Image Generation) → Comic Panels
```

### Three-Pass Prompt Generation

1. **Style Analysis** (optional): Analyze reference image to extract prompt-engineering keywords
2. **Character Sheet Extraction**: Create consistent visual descriptions for all characters
3. **Panel Prompt Generation**: Generate panel prompts with character descriptions injected

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Create a `.env` file in the `backend_ComicGen` directory:

```env
# Required: Claude API (prompt generation)
ANTHROPIC_API_KEY=your_anthropic_api_key

# Required: ElevenLabs API (audio transcription)
ELEVENLABS_API_KEY=your_elevenlabs_api_key

# Required: Gemini API (image generation)
GEMINI_API_KEY=your_gemini_api_key
```

### 3. Run the Server

```bash
uvicorn app.main:app --reload --port 8000
```

## API Endpoints

### Audio Processing

- `POST /audio/transcribe` - Transcribe audio file to comic script
- `POST /audio/generate-comic` - Full pipeline: audio → comic panels

### Pipeline

- `POST /pipeline/run` - Run pipeline from transcript
- `POST /pipeline/generate-prompts` - Generate prompts only (no images)
- `GET /pipeline/health` - Check service health

### Gemini

- `POST /gemini/generate-panel` - Generate single panel image
- `POST /gemini/generate-batch` - Generate multiple panel images
- `GET /gemini/health` - Check Gemini service health

## Usage Examples

### Generate Comic from Audio

```bash
curl -X POST "http://localhost:8000/audio/generate-comic" \
  -F "file=@audio.mp3" \
  -F "style=storybook" \
  -F "prompt_temperature=0.3"
```

### Generate Comic with Style Reference

```bash
curl -X POST "http://localhost:8000/audio/generate-comic" \
  -F "file=@audio.mp3" \
  -F "style_reference=@style_image.png" \
  -F "style=storybook"
```

### Generate Prompts Only (Testing)

```bash
curl -X POST "http://localhost:8000/pipeline/generate-prompts" \
  -H "Content-Type: application/json" \
  -d '{
    "comic_script": [
      {"start_s": 0, "end_s": 5, "lyric_snippet": "Once upon a time..."}
    ],
    "temperature": 0.3
  }'
```

## Testing

```bash
python test_claude_pipeline.py
```

## Project Structure

```
backend_ComicGen/
├── app/
│   ├── main.py                 # FastAPI application
│   ├── api/
│   │   ├── audio_routes.py     # Audio endpoints
│   │   ├── pipeline_routes.py  # Pipeline endpoints
│   │   └── gemini_routes.py    # Gemini endpoints
│   ├── services/
│   │   ├── claude_prompt_service.py  # Claude prompt generation
│   │   ├── pipeline.py               # Pipeline orchestrator
│   │   └── gemini_service.py         # Gemini image generation
│   └── models/
│       └── claude_schemas.py   # Pydantic models
├── transcription.py            # ElevenLabs transcription
├── requirements.txt
└── test_claude_pipeline.py     # Test suite
```

## Key Features

- **Three-Pass Architecture**: Style analysis → Character extraction → Panel generation
- **Tool Use (Function Calling)**: Guaranteed structured JSON output from Claude
- **Character Consistency**: Character descriptions programmatically injected based on `characters_present` list
- **Style Consistency**: Style keywords extracted from reference image and appended to all prompts
- **Pronoun Handling**: Works even when scene descriptions use pronouns instead of character names
