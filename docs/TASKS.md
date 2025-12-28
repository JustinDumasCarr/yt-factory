# Tasks

Short-term execution queue.
Keep **Now** to 10–20 items max.

If you're an LLM/agent: start at `AGENTS.md`, then execute tasks from **Now** top to bottom.
Default behavior: do the **first unchecked** task in **Now**.

Legend:
- [ ] not started
- [~] in progress
- [x] done
- [!] blocked

---

## Now

- [ ] T006 Roman inscription thumbnail text (Cinzel, spacing, outline, shadow)
  - Verify: make test
  - Notes:
    - Two centered text lines on 16:9 image
    - Cinzel Bold for title, Cinzel Regular for subtitle (fallback allowed)
    - ALL CAPS + wide letter spacing via manual spacing
    - Color #F6F6F0
    - Subtle outline + soft drop shadow
    - Title position: y=0.66h, subtitle position: y=0.78h
    - Subtitle source: `project.json.channel.title` if present, otherwise omit
    - Implementation scope: update ffmpeg overlay + render step text preprocessing only

---

## Archive (completed)

### A. Scaffolding
- [x] Create repo structure: `src/`, `docs/`, `projects/`
  - Acceptance: folders exist, projects/ is gitignored
- [x] Add `.env.example`
  - Acceptance: contains keys for Gemini, Suno, YouTube OAuth paths, optional defaults
- [x] Add `docs/ROADMAP.md` and `docs/TASKS.md`
  - Acceptance: these files exist and are linked in README

### B. Project state + logging
- [x] Implement project folder creation and id generation
  - Acceptance: `ytf new` creates `projects/<id>/` with subfolders and `project.json`
- [x] Implement read/write helpers for `project.json`
  - Acceptance: all commands can load and update project.json reliably
- [x] Implement per-step logs
  - Acceptance: each step writes to `logs/<step>.log`
- [x] Implement status updates + last error persistence
  - Acceptance: on failure, `project.json.status.last_error` includes message + stack + step

### C. CLI command skeleton
- [x] Implement CLI entry and commands: `new`, `plan`, `generate`, `render`, `upload`
  - Acceptance: commands run and print friendly output without doing real work yet
- [x] Implement `ytf doctor` command (sanity checks)
  - Checks: FFmpeg installed, env vars present, writable projects dir
  - Acceptance: returns non-zero exit code on missing prerequisites

### D. Gemini provider
- [x] Implement Gemini client wrapper
  - Acceptance: one function can call Gemini and return text reliably
- [x] Implement `plan` step (prompts + optional lyrics + YouTube metadata)
  - Acceptance: writes `plan.prompts[]` and `plan.youtube_metadata` to project.json
- [x] Add prompt templates and constraints
  - Acceptance: vocals OFF creates instrumental prompts; vocals ON creates prompt+lyrics pairs

### E. Suno provider
- [x] Implement Suno client wrapper using your API key
  - Acceptance: can submit a generation job and get back a job id
- [x] Implement polling + download
  - Acceptance: downloads audio to `tracks/` and records local path
- [x] Compute duration for downloaded tracks
  - Acceptance: each track in project.json has `duration_seconds`

### F. Rendering (FFmpeg)
- [x] Implement track filtering (use all ok tracks)
  - Acceptance: uses all tracks with status==ok and audio_path exists, sorted by track_index
- [x] Implement loudness normalization (simple v1)
  - Acceptance: output audio does not vary wildly in volume (basic loudnorm)
- [x] Implement static image mux to MP4
  - Acceptance: produces `output/final.mp4` at 1080p 30fps
- [x] Generate chapters and description files
  - Acceptance: `output/chapters.txt` and `output/youtube_description.txt` exist
- [x] Implement background image generation with Gemini
  - Acceptance: generates theme-appropriate background using Gemini 2.5 Flash Image API per-project (hard gate: render fails if generation fails, no upload without background)
- [x] Implement thumbnail creation with text overlay
  - Acceptance: creates `assets/thumbnail.png` with album title and theme text overlaid

### G. YouTube upload
- [x] Implement OAuth token caching
  - Acceptance: first run authenticates, subsequent runs reuse token
- [x] Implement resumable upload
  - Acceptance: uploads mp4 and returns a video id
- [x] Apply metadata (title/description/tags/privacy/category/language/made_for_kids)
  - Acceptance: uploaded video matches channel-driven settings
- [x] Persist YouTube results to project.json
  - Acceptance: `youtube.video_id`, `thumbnail_uploaded`, `thumbnail_path` are saved
- [x] Auto thumbnail upload
  - Acceptance: if thumbnail exists, automatically uploads and persists status
- [x] Idempotent upload behavior
  - Acceptance: re-running upload step skips if video_id already exists and thumbnail uploaded; if video uploaded but thumbnail missing, retries thumbnail upload

### Next (high leverage improvements)
- [x] Channel-driven workflow:
  - [x] Channel profiles (YAML configs) with defaults, constraints, templates
  - [x] `ytf new` requires `--channel` and uses channel defaults
  - [x] `plan` step applies channel constraints and validates metadata
  - [x] Funnel outputs: templated descriptions + pinned comments with CTA
  - Acceptance: channel profiles drive all steps, funnel outputs include CTAs
- [x] `approved.txt` support (manual gate)
  - Acceptance: if file exists, only listed tracks are rendered
- [x] Auto-filter bad tracks (QC step):
  - [x] reject too short
  - [x] reject long initial silence
  - [x] reject missing/corrupt files
  - Acceptance: filtered tracks are marked in project.json with reason, QC reports generated
- [x] Review/QC step:
  - [x] `ytf review` command
  - [x] QC checks (duration, leading silence, file integrity)
  - [x] Generate `qc_report.json` and `qc_report.txt`
  - [x] Honor `approved.txt` and `rejected.txt`
  - Acceptance: review step runs between generate and render, persists QC results
- [x] Retry/backoff wrapper for batch mode
  - Acceptance: retry logic applied to plan/generate/upload steps in batch context, transient errors retried with exponential backoff
- [x] `ytf run <id>` convenience command
  - Runs plan -> generate -> review -> render -> upload (or up to --to step)
  - Acceptance: stops at failed step and leaves good logs, skips upload if already uploaded
- [x] `ytf batch` command
  - Creates N projects and runs them sequentially
  - Acceptance: generates batch_summary.json with per-project outcomes, never hides failures
- [x] Queue-based batch processing v2:
  - [x] `ytf queue add/ls/run` commands
  - [x] File-based queue with pending/in_progress/done/failed lifecycle
  - [x] Per-project and per-track attempt caps in project.json schema
  - [x] Partial resume for generate step (skips completed tracks, retries failed under cap)
  - [x] Queue run summaries (JSON + log per run)
  - Acceptance: `ytf queue run` processes items sequentially, resumes after interruption, respects attempt caps
