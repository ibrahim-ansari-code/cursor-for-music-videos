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
