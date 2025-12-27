# Project schema

Each project is a folder containing:
- project.json
- tracks/
- assets/
- output/
- logs/

## Folder layout
projects/<project_id>/
  project.json
  tracks/
  assets/
    background.png
  output/
    final.mp4
    chapters.txt
    youtube_description.txt
  logs/
    plan.log
    generate.log
    render.log
    upload.log

## project.json shape (v1)
Top-level fields:
- project_id: string
- created_at: iso string
- theme: string
- target_minutes: number (default 60)
- track_count: number (default 25)
- vocals: { enabled: boolean }
- lyrics: { enabled: boolean, source: "gemini" | "manual" }
- video: { width: 1920, height: 1080, fps: 30 }
- upload: { privacy: "unlisted" | "private" | "public" }

State and outputs:
- status:
  - current_step: "new" | "plan" | "generate" | "render" | "upload" | "done"
  - last_successful_step: same enum
  - last_error: { step, message, stack, at } | null

Planning:
- plan:
  - prompts: [{ track_index, prompt, seed_hint, vocals_enabled, lyrics_text? }]
  - youtube_metadata: { title, description, tags[] }

Generated tracks:
- tracks: [
    {
      track_index,
      prompt,
      provider: "suno",
      job_id,
      audio_path,
      duration_seconds,
      status: "ok" | "failed",
      error?: { message, raw }
    }
  ]

Render:
- render:
  - background_path
  - selected_track_indices[]
  - output_mp4_path
  - chapters_path
  - description_path

Upload:
- youtube:
  - video_id
  - uploaded_at
  - privacy
  - title
