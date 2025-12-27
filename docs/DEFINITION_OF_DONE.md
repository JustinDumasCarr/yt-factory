# Definition of Done

This file defines when each step is considered complete.
If a step does not meet these criteria, it is not done.

---

## Global requirements (all steps)
- Writes to the correct per-step log file in `projects/<id>/logs/<step>.log`.
- Updates `project.json.status.current_step` when starting.
- Updates `project.json.status.last_successful_step` on success.
- On failure:
  - sets `project.json.status.last_error.step`
  - sets `message`
  - sets `stack` (full traceback)
  - keeps partial outputs for debugging (do not delete).

---

## Step: new
Done when:
- `projects/<id>/` is created with:
  - `tracks/`, `assets/`, `output/`, `logs/`
  - `project.json` created and valid
- `project.json` contains:
  - project_id, created_at
  - theme, target_minutes, track_count
  - vocals/lyrics settings
  - video settings (1080p, 30fps)
  - upload default (unlisted)

---

## Step: plan (Gemini)
Done when:
- `project.json.plan` exists and includes:
  - `prompts[]` length == track_count (or clearly documented if fewer)
  - each prompt has track_index and a non-empty prompt string
- If vocals enabled:
  - each prompt includes `lyrics_text` OR plan explicitly indicates lyrics source is not Gemini
- `project.json.plan.youtube_metadata` includes:
  - title (non-empty)
  - description (non-empty)
  - tags (array, can be empty)
- No forbidden content in generated lyrics:
  - no artist references
  - no copyrighted lyrics snippets
  - no brand names
  - if detected, mark that prompt as invalid and regenerate or skip

---

## Step: generate (Suno)
Done when:
- For each planned prompt:
  - either a track is generated successfully OR it is marked failed with an error
- For successful tracks:
  - audio file exists in `tracks/`
  - `project.json.tracks[]` entry contains:
    - track_index
    - provider
    - job_id (if applicable)
    - audio_path (relative or absolute, but consistent)
    - duration_seconds (must be > 0)
    - status = "ok"
- For failed tracks:
  - `status = "failed"`
  - error.message exists
  - error.raw exists if available
- Generation step must not crash due to one failed track.

---

## Step: render (FFmpeg)
Done when:
- Background image exists (default `assets/background.png`) OR a configured alternative is present.
- Track selection is recorded in `project.json.render.selected_track_indices[]`.
- Output files exist:
  - `output/final.mp4`
  - `output/chapters.txt`
  - `output/youtube_description.txt`
- Output MP4 properties:
  - video: 1920x1080, 30fps
  - audio present and not silent
  - duration is within:
    - target_minutes ± 5 minutes (v1 tolerance)
- Chapters file:
  - starts at 00:00
  - contains entries for each included track in correct order

---

## Step: upload (YouTube)
Done when:
- OAuth token is cached locally after first auth.
- Video is uploaded via resumable upload successfully.
- `project.json.youtube` contains:
  - video_id
  - uploaded_at
  - privacy
  - title used
- Uploaded video metadata matches project settings:
  - title
  - description includes chapters
  - privacy defaults to unlisted unless overridden

---

## Optional: run (end-to-end)
Done when:
- Running `ytf run <id>` executes plan -> generate -> render -> upload
- If any step fails:
  - stops immediately
  - logs clearly indicate the failing step
  - project.json.last_error is populated
  - prior successful outputs remain intact
