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
    pinned_comment.txt
    qc_report.json
    qc_report.txt
  logs/
    plan.log
    generate.log
    review.log
    render.log
    upload.log

## project.json shape (v2 - channel-driven)
Top-level fields:
- project_id: string
- created_at: iso string
- theme: string
- channel_id: string (required, e.g., "cafe_jazz", "fantasy_tavern")
- intent: string (e.g., "music_compilation", "sleep", "focus")
- target_minutes: number (default 60, channel-driven)
- track_count: number (default 25, channel-driven)
- vocals: { enabled: boolean }
- lyrics: { enabled: boolean, source: "gemini" | "manual" }
- video: { width: 1920, height: 1080, fps: 30 }
- upload: { privacy: "unlisted" | "private" | "public" }
- funnel: { landing_url?, utm_source?, utm_campaign?, cta_variant_id? }

State and outputs:
- status:
  - current_step: "new" | "plan" | "generate" | "review" | "render" | "upload" | "done"
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
      error?: { message, raw },
      qc?: {
        passed: boolean,
        issues: [{ code, message, value? }],
        measured: { duration_seconds?, leading_silence_seconds?, ... }
      }
    }
  ]

Review/QC:
- review:
  - qc_report_json_path
  - qc_report_txt_path
  - approved_track_indices[]
  - rejected_track_indices[]
  - qc_summary: { passed_count, failed_count, ... }

Render:
- render:
  - background_path
  - selected_track_indices[]
  - output_mp4_path
  - chapters_path
  - description_path

Upload:
- upload:
  - privacy: "unlisted" | "private" | "public"
  - category_id: string (default "10" for Music)
  - made_for_kids: boolean
  - default_language: string (default "en")
- youtube:
  - video_id
  - uploaded_at
  - privacy
  - title
  - thumbnail_uploaded: boolean
  - thumbnail_path: string | null
