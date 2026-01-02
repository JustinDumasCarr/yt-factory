# Project schema

Each project is a folder containing:
- project.json
- tracks/
- assets/
- output/
- logs/

## Folder layout

### Project folder
projects/<project_id>/
  project.json
  tracks/
  assets/
    background.png (Gemini-generated per project; required for upload)
    thumbnail.png (generated per project; required for upload)
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

### Brand assets folder (repo root)
assets/brand/<channel_id>/
  (Backgrounds are not stored here; each project generates its own background.)
  font.ttf or font.otf (custom font override, optional)
  thumbnail_template.png (optional, future use)

### Soundbank folder (repo root, global)
assets/soundbank/
  soundbank.json (metadata: list of available sounds with IDs, paths, durations)
  <sound_id>.mp3 (or .wav) - Reusable audio stems for tinnitus channel
  <sound_id>.mp3
  ...
  
  Example structure:
  - soundbank.json
  - rain_gentle_001.mp3
  - crickets_night_001.mp3
  - ocean_waves_001.mp3
  - cicadas_summer_001.mp3

## project.json shape (v2 - channel-driven)
Top-level fields:
- project_id: string
- created_at: iso string
- theme: string
- channel_id: string (required, e.g., "cafe_jazz", "fantasy_tavern")
- intent: string (e.g., "music_compilation", "sleep", "focus")
- target_minutes: number (default 60, channel-driven)
  - Used as minimum duration for render step if less than channel minimum (allows test projects with fewer tracks)
- track_count: number (default 25, channel-driven)
- vocals: { enabled: boolean }
- lyrics: { enabled: boolean, source: "gemini" | "manual" }
- video: { width: 1920, height: 1080, fps: 30 }
- upload: { privacy: "unlisted" | "private" | "public" }
- funnel: { landing_url?, utm_source?, utm_campaign?, cta_variant_id? }
- tinnitus_recipe?: { stems: [{ sound_id, volume }], mix_type: "single" | "layered", target_duration_seconds }
  - Only present for tinnitus channel projects
  - References sounds from global soundbank (assets/soundbank/)
  - mix_type: "single" loops one stem, "layered" mixes multiple stems

State and outputs:
- status:
  - current_step: "new" | "plan" | "generate" | "review" | "render" | "upload" | "done"
  - last_successful_step: same enum
  - last_error: { step, message, stack, at } | null

Planning:
- plan:
  - prompts: [{ job_index, style, title, prompt, seed_hint, vocals_enabled, lyrics_text? }]
    - Note: `job_index` replaces old `track_index` (backwards compatible)
    - Each job produces 2 variants (tracks)
  - youtube_metadata: { title, description, tags[] }

Generated tracks:
- tracks: [
    {
      track_index,  # Sequential index across all variants (0, 1, 2, 3, ...)
      title,  # Variant-specific title (e.g., "Whispering Scrolls I" or "Whispering Scrolls II")
      style,  # Music style/genre (from job prompt)
      prompt,  # Musical description
      provider: "suno",
      job_id,  # Suno job ID (shared across both variants from same job)
      job_index,  # Which planned job this came from (0-based)
      variant_index,  # Which variant (0 or 1) from the job
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
  - background_path (per-project generated)
  - thumbnail_path (per-project generated with channel styling)
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
