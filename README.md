0) Core invariant (what the whole system guarantees)
Invariant A — audio is the source of truth for timing
audio_duration_s is canonical.


Every visual scene is a silent clip with a duration that sums to audio_duration_s.


The final exported MP4 has the original mp3 muxed in and is trimmed/padded to exactly match audio_duration_s.


Invariant B — frontend media is never forwarded directly
Frontend uploads once to backend.


Backend persists to object storage.


Everything downstream uses audio_url / image_url (signed URL or public URL).



1) Frontend upload
Frontend upload (audio.mp3 + theme_image)
UI action:
User selects audio.mp3 and theme_image.(png/jpg/webp)


Optional user_options (style tags, cut frequency, number of scenes, intensity, etc.)


Request
 → POST /uploads (multipart/form-data)
fields:


audio (required, mp3/wav/m4a)


image (required)


user_options (optional JSON string)


Backend response
{ audio_upload_id, image_upload_id, audio_url, image_url }


audio_url and image_url are either:


signed URLs valid for N minutes, or


permanent public URLs if you're okay with that



2) Backend validate + persist
Backend API validate + persist
Validation rules
audio is present and is an allowed format, size cap, duration cap


image is present and is allowed format, size cap


enforce content-length limits early


Storage
 → PUT audio.mp3 to Object Storage (S3/R2)
 → PUT theme_image to Object Storage (S3/R2)
Outputs
audio_url: stable object URL (or stable key + signed fetch)


image_url: stable object URL


Create job
→ POST /jobs {audio_url, image_url, user_options}
Backend does
creates a DB row:


job_id (uuid)


status = queued


progress = 0


audio_url, image_url


user_options (JSON)


created_at, updated_at


placeholders for: audio_duration_s, segments_json, scenes_json, final_video_url, global_style, global_mood


enqueue job_id


Response
returns { job_id } to frontend



3) Frontend progress
Frontend progress
→ GET /jobs/:job_id (poll every 1–3s, exponential backoff if long)
Response shape
{
  "job_id": "…",
  "status": "queued|running|generating_scenes|composing|done|failed",
  "progress": 0.0,
  "message": "human-readable",
  "final_video_url": null,
  "global_mood": null,
  "global_style": null,
  "error": null
}


4) Queue → Worker
Queue
→ Worker receives { job_id }
Worker fetches job record from DB to get:
audio_url, image_url, user_options



5) Worker timing prep
Worker timing prep
Goal: produce audio_duration_s and (optionally) a first-pass segment template.
Steps:
Fetch audio metadata


(HEAD request) to confirm file exists + content-type + size


ffprobe (canonical duration)


audio_duration_s = exact float seconds


Segments template


If you want a baseline before STT:


fixed window segments, e.g. 4.0s each, last is remainder


store as:


segments_template = [{start_s, end_s}]


Persist
update job:


audio_duration_s


status = running


progress ~ 0.1



6) Worker lyrics + timestamps (ElevenLabs STT)
Worker lyrics + timestamps
Goal: attempt to extract lyrics-like text + time alignment.
→ POST ElevenLabs Speech-to-Text
payload uses cloud_storage_url: audio_url (so no reupload)


outputs: transcript text, and if available, timing info (word/segment timestamps)


Important edge case
If the track is instrumental or vocals are unclear:


transcript may be empty or low-quality.


timing may be missing.


Your pipeline must still work.


Normalize transcript
transcript_clean:


strip repeated filler, collapse whitespace


keep punctuation minimal (LLMs hate messy STT)



7) Build segments[] aligned to audio_duration_s (timestamped)
Build segments[] = [{start_s,end_s,lyric_snippet}]
Goal: segments drive scene timing; scenes must match segments exactly.
You choose ONE of these segmentation strategies:
Strategy A (recommended baseline): fixed windows
Use scene_len_s from user_options (default 4.0s)


segments[i] = {start_s=i*scene_len_s, end_s=min(duration,(i+1)*scene_len_s)}


lyric_snippet is best-effort:


if STT timestamps exist: include words within segment


else: take proportional slice from transcript or leave empty


Strategy B (better, if timing exists): word-timestamp aggregation
Group words into segments by time boundaries.


Ensure no gaps/overlaps.


For each segment:


lyric_snippet = join(words_in_range)


Strategy C (best feel): section-based segments
Detect sections (intro/verse/chorus) using an audio analyzer (not ElevenLabs)


Then subdivide each section by beat or fixed window.


This requires additional DSP.


Schema
[
  {
    "i": 0,
    "start_s": 0.0,
    "end_s": 4.0,
    "lyric_snippet": "…",
    "energy_hint": 0.42
  }
]

Persist:
segments_json


status = running


progress ~ 0.25



8) Worker start Gumloop run
Worker start Gumloop run
→ POST https://api.gumloop.com/api/v1/start_pipeline
pipeline_inputs must include:
image_url


transcript_clean


segments_json


audio_duration_s


user_options (JSON)


Outputs
gumloop_run_id


Persist:
gumloop_run_id


status = running


progress ~ 0.35



9) Gumloop flow (internal, explicit responsibilities)
Gumloop Flow: node-by-node
Flow inputs
image_url


transcript_clean


segments[]


audio_duration_s


user_options


Node 1 — Ask AI: GLOBAL MOOD + GLOBAL STYLE
Responsibility
Produce one coherent visual identity for the entire video.


Inputs
transcript_clean


image_url


optional user_options.style_tags


Outputs (must be structured JSON)
{
  "global_mood": "…",
  "global_style": "…",
  "palette": ["…"],
  "motifs": ["…"],
  "do_not_include": ["…"]
}

Node 2 — Ask AI: SCENE PROMPTS (timestamp-locked)
Responsibility
For each segment:


keep {start_s,end_s} unchanged


generate scene-specific prompt/camera/motion


ensure continuity across scenes


Inputs
global_mood, global_style, segments[], image_url


Outputs
{
  "scenes": [
    {
      "i": 0,
      "start_s": 0.0,
      "end_s": 4.0,
      "prompt": "...",
      "camera": "...",
      "motion": "...",
      "negative_prompt": "..."
    }
  ]
}

Hard constraints in the prompt
timestamps unchanged


count of scenes equals segments length


no gaps/overlaps


visuals match mood arc implied by lyric_snippet + energy_hint


Node 3 — Output Node
Emits:
global_mood


global_style


scenes[] (as JSON string)


optionally thumbnail_prompt etc.


(Outputs are what get_pl_run returns.)

10) Worker poll Gumloop outputs
→ GET https://api.gumloop.com/api/v1/get_pl_run?run_id=...
Receives
{ global_mood, global_style, scenes[] }


Validate before using:
scenes.length == segments.length


each scene has same timestamps


final scenes[last].end_s == audio_duration_s (within epsilon 0.02s)


Persist:
scenes_json, global_mood, global_style


status = generating_scenes


progress ~ 0.55



11) Worker generate silent scene clips (external video model)
Generate clips per scene
For each scene:
 → POST VideoGenAPI
input:


prompt


ref_image_url = image_url (style anchor)


duration_s = end_s - start_s


style = global_style


optional: negative_prompt, seed (for consistency)


Outputs
either immediate clip_url


or provider_job_id


If async:
poll provider until ready


store clip_url


Persist:
clip_urls[] as you go


update progress incrementally (e.g., 0.55 → 0.85)



12) Worker compose final music video with original audio
Compose
Download/stream clip_urls[]


ffmpeg concat silent clips → temp_video.mp4


ffmpeg mux temp_video + original audio_url → final_video.mp4


trim/pad to exactly audio_duration_s


Hard constraints
final duration matches audio


audio is original, unmodified (unless user wants fade in/out)


Set status = composing
 Set progress ~ 0.9

13) Worker store final output + update job
→ PUT final_video.mp4 to Object Storage
 → get final_video_url
→ PATCH /jobs/:job_id
status = done


final_video_url


global_mood, global_style


optionally scenes_json for debugging



14) Frontend completion
Frontend polls:
 → GET /jobs/:job_id
Receives:
final_video_url


optional global_mood, global_style


Frontend plays final mp4.
