# Tasks

Short-term execution list.
Keep **Now** to 10–20 items so it stays actionable.

If you're an LLM/agent: start at `AGENTS.md`, then execute tasks from **Now** top to bottom.
Default behavior: do the **first unchecked** task.

Legend:
- [ ] not started
- [~] in progress
- [x] done
- [!] blocked

---

## Now (active queue)

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

## Later (optional)

- [ ] T001 Runway 10s intro slot
  - Verify: make test
- [ ] T002 Creatomate title card clip
  - Verify: make test
- [ ] T003 StorageAdapter + S3
  - Verify: make test
- [ ] T004 Docker packaging for server runs
  - Verify: make test
- [ ] T005 Minimal GUI wrapper (FastAPI or Streamlit)
  - Verify: make test

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
  - Acceptance: creates `assets/thumb
