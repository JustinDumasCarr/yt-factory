# Workflow

This is a step-based CLI pipeline.

Steps:
1. new
2. plan
3. generate
4. review (QC + approvals)
5. render
6. upload

## Project lifecycle
### 1) Create project
Creates a project folder and `project.json` with user inputs:
- theme
- channel_id (required, e.g., "cafe_jazz", "fantasy_tavern")
- target_minutes (from channel profile, can override)
- track_count (from channel profile, can override)
- vocals_mode (on/off, defaults to channel profile)
- lyrics_mode (if vocals on)
- video settings (1080p, 30fps)
- upload settings (from channel profile)
- funnel config (initialized, populated in plan step)

### 2) Plan (Gemini, channel-driven)
Generates:
- music prompt variants for Suno (applies channel constraints: banned terms, style guidance, energy level)
- optional lyrics for each track if vocals are on
- YouTube metadata draft: title, description, tags (validated against channel tag rules)
- Chooses CTA variant from channel profile and persists to `project.funnel.cta_variant_id`
Writes into `project.json` under `plan`.

### 3) Generate (Suno)
For each prompt:
- submit generation job
- poll until ready
- download audio file(s)
- compute duration
- write `tracks[]` metadata into `project.json`

Failure policy:
- if one track fails, continue with the rest
- record error per track

### 4) Review (QC + approvals)
Runs quality control checks on all tracks:
- Duration check (reject too short)
- Leading silence detection (reject excessive silence)
- File integrity check (reject missing/corrupt files)
- Honors `approved.txt` (manual allowlist)
- Honors `rejected.txt` (manual blocklist)

Outputs:
- `output/qc_report.json` (structured QC data)
- `output/qc_report.txt` (human-readable report)
- Persists QC results to `project.json` (per-track `qc` field, project-level `review` section)

### 5) Render (FFmpeg local, honors QC/approvals)
Track selection:
- If `approved.txt` exists: use only approved tracks (still require status=="ok" and file exists)
- Else: use all tracks where `status=="ok"` and `qc.passed==True`
- Fail fast if total duration is below channel minimum

Process:
- choose background image from `assets/background.png` (or configured path)
- concatenate audio tracks until target length reached
- normalize loudness
- mux static image + audio into final MP4

Outputs:
- `output/final.mp4`
- `output/chapters.txt`
- `output/youtube_description.txt` (templated with channel description + CTA)
- `output/pinned_comment.txt` (short + long CTA variants)

### 6) Upload (YouTube Data API)
- OAuth auth flow, token cached locally
- resumable upload
- apply metadata and upload settings
- record returned video ID in `project.json`
