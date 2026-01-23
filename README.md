# Comic & Audio Studio

An AI-powered platform that transforms audio into stunning comic book panels and converts images into immersive audiobooks.

## Overview

This project provides two powerful AI-driven modules:

1. **Audio to Comic**: Convert audio files or URLs into visually rich comic book panels with synchronized captions
2. **Images to Audio**: Transform a series of images into a cohesive audiobook experience

Built with modern web technologies and leveraging cutting-edge AI services for transcription, prompt generation, and image synthesis.

## Features

### Audio to Comic
- **Multi-format Support**: Upload audio files (MP3, WAV, M4A) or paste audio URLs
- **Intelligent Transcription**: Automatic speech-to-text with word-level timestamps using ElevenLabs
- **AI-Powered Scene Generation**: Claude AI analyzes audio content and generates contextual comic panel prompts
- **Visual Consistency**: Character extraction and style consistency across panels
- **Dynamic Panel Layout**: Automatically organizes panels into pages with optimal spacing
- **Image Generation**: Gemini AI creates comic-style images based on generated prompts

### Comic to Audio
- **Batch Image Processing**: Process multiple images from URLs
- **Narrative Generation**: AI creates cohesive storytelling from image sequences
- **Audio Synthesis**: Convert narrative into natural-sounding audio

## Architecture

### Technology Stack

#### Audio to Comic Tech Stack

**Frontend:**
- Next.js 16 (React 19)
- TypeScript
- Tailwind CSS
- GSAP for animations

**Backend:**
- FastAPI (Python)
- ElevenLabs API (Speech-to-Text for audio transcription)
- Anthropic Claude API (Prompt Generation for scene descriptions)
- Google Gemini API (Image Generation for comic panels)

#### Comic to Audio Tech Stack

**Frontend:**
- Next.js 16 (React 19) - Shared frontend application
- TypeScript
- Tailwind CSS

**Backend:**
- FastAPI (Python)
- Gumloop API (Image analysis and narrative generation)
- ElevenLabs API (Text-to-Speech for audio synthesis)
- pydub (Audio processing and stitching)
- SQLite (Voice caching via VoiceCache for character voice consistency)

## Project Structure

```
cursor-for-music-videos/
├── frontend/                    # Next.js frontend
│   ├── app/                    # Pages (comic, audiobook)
│   └── components/             # React components
│
├── backend_ComicGen/           # Audio → Comic backend
│   ├── app/
│   │   ├── api/               # API routes
│   │   ├── services/          # Pipeline, Claude, Gemini services
│   │   └── models/            # Data models
│   └── requirements.txt
│
└── backend-audio-gen/          # Comic → Audio backend
    ├── main.py                # FastAPI app
    ├── audio.py               # Audio processing
    ├── elevenlabs_client.py  # TTS integration
    └── requirements.txt
```

## Getting Started

### Prerequisites

- **Node.js** 18+ and npm
- **Python** 3.10+
- **API Keys**:
  - Anthropic Claude API key
  - ElevenLabs API key
  - Google Gemini API key

### Installation

#### 1. Clone the Repository

```bash
git clone <repository-url>
cd cursor-for-music-videos
```

#### 2. Frontend Setup

```bash
cd frontend
npm install
```

#### 3. Backend Setup (Comic Generation)

```bash
cd backend_ComicGen
pip install -r requirements.txt
```

Create a `.env` file in `backend_ComicGen/`:

```env
ANTHROPIC_API_KEY=your_anthropic_api_key
ELEVENLABS_API_KEY=your_elevenlabs_api_key
GEMINI_API_KEY=your_gemini_api_key
```

#### 4. Backend Setup (Audio Generation)

```bash
cd backend-audio-gen
pip install -r requirements.txt
```

Create a `.env` file in `backend-audio-gen/` with your ElevenLabs API key.

### Running the Application

#### Start the Frontend

```bash
cd frontend
npm run dev
```

The frontend will be available at `http://localhost:3000`

#### Start the Comic Generation Backend

```bash
cd backend_ComicGen
uvicorn app.main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`

#### Start the Audio Generation Backend

```bash
cd backend-audio-gen
uvicorn main:app --reload --port 8001
```

The API will be available at `http://localhost:8001`

> **Note**: Make sure to update the frontend API endpoints to match your backend URLs if they differ from the defaults.

## Usage

### Audio to Comic

1. Navigate to the main page
2. Select "Audio to Comic" module
3. Choose to upload an audio file or paste an audio URL
4. Click "POW! GENERATE COMIC"
5. Wait for the AI to:
   - Transcribe the audio
   - Analyze content and extract characters
   - Generate scene descriptions
   - Create comic panel images
   - Organize panels into pages
6. View and download your generated comic book

### Images to Audio

1. Navigate to the main page
2. Select "Images to Audio" module
3. Paste one or more image URLs (PNG/JPG)
4. Click "BAM! GENERATE AUDIO"
5. Wait for the AI to process images and generate audio
6. Listen to or download the generated audiobook

## API Endpoints

### Comic Generation Backend

#### Audio Processing
- `POST /audio/transcribe` - Transcribe audio file to text with timestamps
- `POST /audio/generate-comic` - Full pipeline: audio → comic panels

#### Pipeline
- `POST /pipeline/run` - Run pipeline from transcript
- `POST /pipeline/generate-prompts` - Generate prompts only (no images)
- `GET /pipeline/health` - Check service health

#### Image Generation
- `POST /gemini/generate-panel` - Generate single panel image
- `POST /gemini/generate-batch` - Generate multiple panel images
- `GET /gemini/health` - Check Gemini service health

For detailed API documentation, see [backend_ComicGen/README.md](backend_ComicGen/README.md)

### Example API Usage

#### Generate Comic from Audio

```bash
curl -X POST "http://localhost:8000/audio/generate-comic" \
  -F "file=@audio.mp3" \
  -F "style=storybook" \
  -F "prompt_temperature=0.3"
```

#### Generate Comic with Style Reference

```bash
curl -X POST "http://localhost:8000/audio/generate-comic" \
  -F "file=@audio.mp3" \
  -F "style_reference=@style_image.png" \
  -F "style=storybook"
```

## Development

### Key Features

#### Three-Pass Prompt Generation
1. **Style Analysis** (optional): Analyze reference image to extract prompt-engineering keywords
2. **Character Sheet Extraction**: Create consistent visual descriptions for all characters
3. **Panel Prompt Generation**: Generate panel prompts with character descriptions injected

#### Character Consistency
- Character descriptions are programmatically injected based on `characters_present` list
- Works even when scene descriptions use pronouns instead of character names

#### Style Consistency
- Style keywords extracted from reference image and appended to all prompts
- Global mood and style maintained across all panels

### Testing

#### Test Comic Pipeline

```bash
cd backend_ComicGen
python test_claude_pipeline.py
```

#### Test Audio Pipeline

```bash
cd backend_ComicGen
python test_audio_pipeline.py
```

### Project Architecture Details

- **Tool Use (Function Calling)**: Guaranteed structured JSON output from Claude
- **Dynamic Panel Organization**: Panels are automatically organized into pages with optimal spacing
- **Text Overlay**: Captions are overlaid on panels with comic-style typography
- **Error Handling**: Comprehensive error handling and user feedback throughout the pipeline

## Additional Resources

- [Backend Comic Generation Documentation](backend_ComicGen/README.md) - Detailed backend API documentation
- [FastAPI Documentation](https://fastapi.tiangolo.com/) - FastAPI framework reference
- [Next.js Documentation](https://nextjs.org/docs) - Next.js framework reference

## License

[Add your license information here]

## Contributing

[Add contribution guidelines here]
