# Tasks

This is the short-term execution list.
Keep "Now" to 10-20 items max so it stays actionable.

Legend:
- [ ] not started
- [~] in progress
- [x] done
- [!] blocked

---

## Now (build the full local pipeline)
### A . Scaffolding
- [x] Create repo structure: `src/`, `docs/`, `projects/`
  - Acceptance: folders exist, projects/ is gitignored
- [x] Add `.env.example`
  - Acceptance: contains keys for Gemini, Suno, YouTube OAuth paths, optional defaults
- [x] Add `docs/ROADMAP.md` and `docs/TASKS.md`
  - Acceptance: these files exist and are linked in README

### B . Project state + logging
- [x] Implement project folder creation and id generation
  - Acceptance: `ytf new` creates `projects/<id>/` with subfolders and `project.json`
- [x] Implement read/write helpers for `project.json`
  - Acceptance: all commands can load and update project.json reliably
- [x] Implement per-step logs
  - Acceptance: each step writes to `logs/<step>.log`
- [x] Implement status updates + last error persistence
  - Acceptance: on failure, `project.json.status.last_error` includes message + stack + step

### C . CLI command skeleton
- [x] Implement CLI entry and commands: `new`, `plan`, `generate`, `render`, `upload`
  - Acceptance: commands run and print friendly output without doing real work yet
- [x] Implement `ytf doctor` command (sanity checks)
  - Checks: FFmpeg installed, env vars present, writable projects dir
  - Acceptance: returns non-zero exit code on missing prerequisites

### D . Gemini provider
- [x] Implement Gemini client wrapper
  - Acceptance: one function can call Gemini and return text reliably
- [x] Implement `plan` step (prompts + optional lyrics + YouTube metadata)
  - Acceptance: writes `plan.prompts[]` and `plan.youtube_metadata` to project.json
- [x] Add prompt templates and constraints
  - Acceptance: vocals OFF creates instrumental prompts; vocals ON creates prompt+lyrics pairs

### E . Suno provider
- [x] Implement Suno client wrapper using your API key
  - Acceptance: can submit a generation job and get back a job id
- [x] Implement polling + download
  - Acceptance: downloads audio to `tracks/` and records local path
- [x] Compute duration for downloaded tracks
  - Acceptance: each track in project.json has `duration_seconds`

### F . Rendering (FFmpeg)
- [x] Implement track filtering (use all ok tracks)
  - Acceptance: uses all tracks with status==ok and audio_path exists, sorted by track_index
- [x] Implement loudness normalization (simple v1)
  - Acceptance: output audio does not vary wildly in volume (basic loudnorm)
- [x] Implement static image mux to MP4
  - Acceptance: produces `output/final.mp4` at 1080p 30fps
- [x] Generate chapters and description files
  - Acceptance: `output/chapters.txt` and `output/youtube_description.txt` exist
- [x] Implement background image generation with Gemini
  - Acceptance: generates theme-appropriate background using Gemini 2.5 Flash Image API, falls back to default if fails
- [x] Implement thumbnail creation with text overlay
  - Acceptance: creates `assets/thumbnail.png` with album title and theme text overlaid

### G . YouTube upload
- [ ] Implement OAuth token caching
  - Acceptance: first run authenticates, subsequent runs reuse token
- [ ] Implement resumable upload
  - Acceptance: uploads mp4 and returns a video id
- [ ] Apply metadata (title/description/tags/privacy)
  - Acceptance: uploaded video matches settings, default privacy is Unlisted
- [ ] Persist YouTube results to project.json
  - Acceptance: `youtube.video_id` is saved

---

## Next (high leverage improvements)
- [ ] `approved.txt` support (manual gate)
  - Acceptance: if file exists, only listed tracks are rendered
- [ ] Auto-filter bad tracks:
  - [ ] reject too short
  - [ ] reject long initial silence
  - Acceptance: filtered tracks are marked in project.json with reason
- [ ] Retry/backoff wrapper for all HTTP calls
  - Acceptance: transient errors don’t crash step immediately
- [ ] `ytf run <id>` convenience command
  - Runs plan -> generate -> render -> upload
  - Acceptance: stops at failed step and leaves good logs

---

## Later (optional)
- [ ] Batch mode: generate/render/upload multiple projects from a queue folder
- [ ] Runway 10s intro slot
- [ ] Creatomate title card clip
- [ ] StorageAdapter + S3
- [ ] Docker packaging for server runs
- [ ] Minimal GUI wrapper (FastAPI or Streamlit)
