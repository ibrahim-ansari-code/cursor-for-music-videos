# Music Video Generator - MP3 Transcription Tool

This tool processes MP3 audio files and generates JSON output with lyric segments containing precise timing information using the ElevenLabs Speech-to-Text API.

## Quick Start

### Prerequisites

1. **Install dependencies**:

```bash
pip install -r requirements.txt
```

2. **Set up your API key**:

```bash
# Copy the example env file
cp .env.example .env

# Edit .env and add your ElevenLabs API key
# Get your key from: https://elevenlabs.io/app/settings/api-keys
```

### Transcribe Any MP3 File

Run the transcription script with your MP3 file:

```bash
python3 transcribe_mp3.py "your_song.mp3"
```

The script will:
- Call the ElevenLabs Speech-to-Text API
- Extract word-level and segment-level timestamps
- Output a JSON file with precise timing information

### Examples

```bash
# Basic usage - outputs to your_song_transcription.json
python3 transcribe_mp3.py "my_song.mp3"

# With custom output filename
python3 transcribe_mp3.py "my_song.mp3" --output "custom_output.json"

# With language hint for better accuracy
python3 transcribe_mp3.py "my_song.mp3" --language en
```

## How It Works

The script performs these steps:

1. **API Call**: Sends the MP3 file to ElevenLabs Speech-to-Text API
2. **Transcription**: Receives the full transcript with timing data
3. **Segment Extraction**: Extracts segments with start/end timestamps
4. **Word Extraction**: Extracts individual words with precise timing
5. **JSON Generation**: Creates a structured output file

## Output Format

The generated JSON includes:

```json
{
  "source_file": "song.mp3",
  "transcription": {
    "text": "Full transcription text...",
    "language_code": "en",
    "duration": 45.23
  },
  "segments": [
    {
      "start_s": 0.0,
      "end_s": 5.5,
      "lyric_snippet": "First lyric line..."
    }
  ],
  "words": [
    {
      "start_s": 0.0,
      "end_s": 0.5,
      "word": "First"
    },
    {
      "start_s": 0.5,
      "end_s": 1.0,
      "word": "lyric"
    }
  ]
}
```

## Usage Tips

- Supports MP3, WAV, M4A, OGG, and FLAC audio formats
- The ElevenLabs API provides accurate word-level timestamps
- Use the `--language` flag to improve accuracy for non-English audio
- Segments are automatically detected based on natural speech patterns

## Example Files

After running the transcription:
- Input: `Charlie Kirk Lyrics.mp3` - Sample audio file
- Output: `Charlie Kirk Lyrics_transcription.json` - Generated output with timestamps

---

## Future Pipeline Architecture

Frontend upload (audio.mp3 + theme_image)
→ POST /uploads (multipart/form-data)
→ Backend API

Backend API validate + persist
→ PUT audio.mp3 to Object Storage (S3/R2)
→ PUT theme_image to Object Storage (S3/R2)
→ receive audio_url + image_url
→ POST /jobs {audio_url, image_url, user_options}
→ enqueue job_id
→ return job_id to Frontend

Frontend progress
→ GET /jobs/:job_id (poll)
→ Backend API (status)

Queue
→ Worker (job_id, audio_url, image_url, options)

Worker timing prep
→ fetch audio_url metadata
→ ffprobe audio_url → audio_duration_s
→ (optional) build initial segments template (fixed windows) if needed

Worker lyrics + timestamps
→ POST ElevenLabs Speech-to-Text { cloud_storage_url: audio_url }
→ receive transcript + timestamps (word/segment timing)
→ build segments[] = [{start_s,end_s,lyric_snippet}] aligned to audio_duration_s

Worker start Gumloop run
→ POST https://api.gumloop.com/api/v1/start_pipeline
→ pipeline_inputs: { image_url, transcript, segments[], audio_duration_s, user_options }
→ receive gumloop_run_id

Gumloop flow (internal)
→ Ask AI #1 (GLOBAL MOOD + GLOBAL STYLE) using {transcript, image_url}
→ output global_mood + global_style
→ Ask AI #2 (SCENE PROMPTS) using {global_mood, global_style, segments[]}
→ output scenes[] where each scene keeps exact {start_s,end_s} and adds {prompt,camera,motion,negative_prompt}
→ Output node emits {global_mood, global_style, scenes[]}

Worker poll Gumloop outputs
→ GET https://api.gumloop.com/api/v1/get_pl_run?run_id=gumloop_run_id
→ receive {global_mood, global_style, scenes[]}

Worker generate silent scene clips (external video model)
→ for each scene in scenes[] (in order)
→ POST VideoGenAPI { prompt, ref_image_url:image_url, duration_s:(end_s-start_s), style:global_style }
→ receive clip_url OR provider_job_id
→ if provider_job_id
→ poll VideoGenAPI status until clip_url
→ collect clip_urls[] in order

Worker compose final music video with original audio
→ download/stream clip_urls[]
→ ffmpeg concat clip_urls[] → temp_video.mp4 (duration matches audio_duration_s)
→ ffmpeg mux temp_video.mp4 + audio_url → final_video.mp4
→ trim/pad final_video.mp4 to exactly audio_duration_s

Worker store final output + update job
→ PUT final_video.mp4 to Object Storage
→ receive final_video_url
→ PATCH /jobs/:job_id {status:"done", final_video_url, global_mood, global_style}
→ Backend API

Frontend completion
→ GET /jobs/:job_id
→ receive final_video_url (+ optional global_mood/global_style)
→ play/download final video
