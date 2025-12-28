# Roadmap

This file tracks implementation status at a milestone level.
Granular work lives in `docs/TASKS.md`.

If you're an LLM/agent, start at `AGENTS.md` (repo rulebook + doc router), then come here only for milestone status.

Legend:
- [ ] not started
- [~] in progress
- [x] done
- [!] blocked

---

## Milestone 0 . Repo scaffold (local-first)
Goal: repo has the structure and docs needed to implement cleanly.

- [x] Create folder structure:
  - docs/
  - src/
  - projects/ (gitignored)
- [ ] Add `.env.example` (optional, documented in README)
- [x] Add `AGENTS.md` (agent rulebook + doc router)
- [x] Add baseline docs (overview, workflow, schema, logging)

Exit criteria:
- Repo opens in Cursor, docs are present, and the expected layout exists.

---

## Milestone 1 . Local end-to-end pipeline (no Runway/Creatomate)
Goal: go from theme to an Unlisted YouTube upload on macOS using CLI steps.

- [x] CLI commands exist: `new`, `plan`, `generate`, `render`, `upload`
- [x] Project state management:
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
- [x] YouTube upload integration:
  - [x] OAuth token caching
  - [x] resumable upload
  - [x] apply metadata (title/description/tags/privacy/category/language/made_for_kids)
  - [x] auto thumbnail upload
  - [x] store video_id and thumbnail status

Exit criteria:
- One command sequence produces:
  - `output/final.mp4`
  - `output/chapters.txt`
  - `output/youtube_description.txt`
  - uploaded YouTube video id recorded in project.json

---

## Milestone 2 . Reliability + throughput
Goal: stop babysitting the pipeline.

- [x] Retry/backoff policy for all provider calls
  - Gemini: retry_call wrapper (3 retries, exponential backoff)
  - Suno: retry_call wrapper (3 retries, exponential backoff)
  - YouTube: resumable upload with exponential backoff (up to 10 retries)
- [x] Track-level failures do not kill project (already expected, implemented)
- [x] `approved.txt` support (optional manual gate)
- [x] Auto-filter obvious failures:
  - too short
  - long initial silence
  - missing/failed downloads
- [x] Channel-driven workflow:
  - channel profiles with defaults and constraints
  - funnel outputs (templated descriptions + pinned comments)
  - review/QC step with reports
- [x] Batch mode:
  - [x] run N projects sequentially
  - [x] `ytf run` command for single-project pipeline execution
  - [x] `ytf batch` command with batch summary output
  - [x] retry logic for transient errors in batch context
  - [x] Queue-based batch v2: file-based queue, attempt caps, partial resume
- [x] Improved logs:
  - [x] structured JSON logs optional (enabled via YTF_JSON_LOGS=true)
  - [x] clear error summaries (auto-generated after each step)
  - [x] `ytf logs` command for viewing logs and summaries
  - [x] enhanced queue run summaries with aggregated error statistics

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
