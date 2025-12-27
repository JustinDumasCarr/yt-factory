# Workflow

This is a step-based CLI pipeline.

Steps:
1. new
2. plan
3. generate
4. render
5. upload

## Project lifecycle
### 1) Create project
Creates a project folder and `project.json` with user inputs:
- theme
- target_minutes (default 60)
- vocals_mode (on/off)
- lyrics_mode (if vocals on)
- track_count (default 25)
- video settings (1080p, 30fps)
- upload settings (unlisted by default)

### 2) Plan (Gemini)
Generates:
- music prompt variants for Suno
- optional lyrics for each track if vocals are on
- YouTube metadata draft: title, description, tags
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

Optional manual gate:
- if `approved.txt` exists, only generate or render tracks listed in it
- otherwise, include all generated tracks

### 4) Render (FFmpeg local)
- choose background image from `assets/background.png` (or configured path)
- concatenate audio tracks until target length reached
- normalize loudness
- mux static image + audio into final MP4

Outputs:
- `output/final.mp4`
- `output/chapters.txt`
- `output/youtube_description.txt`

### 5) Upload (YouTube Data API)
- OAuth auth flow, token cached locally
- resumable upload
- apply metadata and upload settings
- record returned video ID in `project.json`
