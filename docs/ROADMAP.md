# Roadmap

This file tracks implementation status at a milestone level.
Granular work lives in `docs/TASKS.md`.

Legend:
- [ ] not started
- [~] in progress
- [x] done
- [!] blocked

---

## Milestone 0 . Repo scaffold (local-first)
Goal: repo has the structure and docs needed to implement cleanly.

- [ ] Create folder structure:
  - docs/
  - src/
  - projects/ (gitignored)
- [ ] Add `.env.example`
- [ ] Add `.cursorrules`
- [ ] Add baseline docs (overview, workflow, schema, logging)

Exit criteria:
- Repo opens in Cursor, docs are present, and the expected layout exists.

---

## Milestone 1 . Local end-to-end pipeline (no Runway/Creatomate)
Goal: go from theme to an Unlisted YouTube upload on macOS using CLI steps.

- [ ] CLI commands exist: `new`, `plan`, `generate`, `render`, `upload`
- [ ] Project state management:
  - create/read/write `project.json`
  - per-step log files
  - status updates + last error persisted
- [x] Gemini integration:
  - generates prompts
  - generates optional lyrics when vocals enabled
  - generates YouTube metadata draft
- [x] Suno integration:
  - create job
  - poll
  - download audio
  - record duration + paths
- [x] Render integration (FFmpeg):
  - use all available tracks (status==ok)
  - generate background images with Gemini
  - create thumbnails with text overlay
  - loudness normalize
  - mux static image to MP4
  - generate chapters
  - generate description text
- [ ] YouTube upload integration:
  - OAuth token caching
  - resumable upload
  - apply metadata
  - store video_id

Exit criteria:
- One command sequence produces:
  - `output/final.mp4`
  - `output/chapters.txt`
  - `output/youtube_description.txt`
  - uploaded YouTube video id recorded in project.json

---

## Milestone 2 . Reliability + throughput
Goal: stop babysitting the pipeline.

- [ ] Retry/backoff policy for all provider calls
- [ ] Track-level failures do not kill project (already expected)
- [ ] `approved.txt` support (optional manual gate)
- [ ] Auto-filter obvious failures:
  - too short
  - long initial silence
  - missing/failed downloads
- [ ] Batch mode:
  - run N projects sequentially
  - optional concurrency limits for generation
- [ ] Improved logs:
  - structured JSON logs optional
  - clear error summaries

Exit criteria:
- Can run overnight batches and wake up to finished renders/uploads.

---

## Milestone 3 . Optional visual upgrades
Goal: better CTR without breaking the core system.

- [ ] Runway 10s intro slot (optional)
- [ ] Creatomate title card clip (optional)
- [ ] Thumbnail generation flow (optional)
- [ ] Consistent branding templates per channel (optional)

Exit criteria:
- Visual enhancements plug in without changing the pipeline core.

---

## Milestone 4 . Server + remote storage (optional)
Goal: run anywhere and store assets off your laptop.

- [ ] Docker support (optional for dev, required on server)
- [ ] StorageAdapter interface:
  - LocalStorage (default)
  - S3Storage (optional)
- [ ] Server runbook:
  - VPS setup
  - cron scheduling
  - environment variables
  - persistent volumes / buckets
- [ ] Simple monitoring:
  - failure notifications (email/discord) optional

Exit criteria:
- Pipeline runs on a server and stores outputs remotely.
