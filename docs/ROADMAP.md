# Roadmap

## Milestone 0 . Repo scaffolding
- [ ] Create folder structure (docs/, projects/, src/)
- [ ] Add .env.example
- [ ] Add docs baseline

## Milestone 1 . Local end-to-end (no Runway/Creatomate)
Goal: go from theme to uploaded Unlisted video on macOS.

- [ ] CLI skeleton with commands: new, plan, generate, render, upload
- [ ] Project state: create/read/write project.json
- [ ] Logging: per-step logs + error persisted in project.json
- [ ] Gemini planner: prompts + optional lyrics + YouTube metadata
- [ ] Suno generator: submit/poll/download + track metadata
- [ ] FFmpeg render: concat + normalize + static image mux + chapters.txt
- [ ] YouTube upload: OAuth + resumable upload + metadata apply

Exit criteria:
- Can produce a 60-minute mp4 and upload it unlisted with chapters.

## Milestone 2 . Quality + productivity
- [ ] approved.txt support (optional manual gate)
- [ ] Auto-filter obvious bad tracks (silence at start, too short)
- [ ] Retry policy + backoff for provider calls
- [ ] Batch mode: run N projects overnight

## Milestone 3 . Visual upgrades (optional)
- [ ] Runway 10s intro slot + caching
- [ ] Creatomate title card clip
- [ ] Thumbnail generation flow

## Milestone 4 . Server + remote storage (optional)
- [ ] Docker support
- [ ] StorageAdapter: Local + S3
- [ ] VPS runbook + cron
