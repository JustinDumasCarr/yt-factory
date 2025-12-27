# yt-factory: Project Overview

## Executive Summary

**yt-factory** is a local-first Python CLI application that automates the creation of music compilation videos and uploads them to YouTube. The project follows a step-based pipeline architecture where each step is resumable and writes its state to a `project.json` file.

**Core Philosophy:**
- Simple, boring code that is easy to debug
- File-based state (no database in v1)
- Step-based pipeline with clear boundaries
- Observable failures with full stack traces
- Local-first execution (macOS primary target)

---

## Technology Stack

### Core Technologies
- **Python 3.10+** - Primary language (required)
- **Typer** - CLI framework
- **Pydantic** - Data validation and models
- **httpx** - HTTP client for API calls
- **python-dotenv** - Environment variable management

### External APIs & Services
- **Google Gemini API** (`google-genai` package)
  - Model: `gemini-2.5-flash` (text generation)
  - Model: `gemini-2.5-flash-image` (image generation)
  - Used for: planning, lyrics generation, YouTube metadata, background images
- **Suno API** (`api.sunoapi.org`)
  - Model: `V4_5ALL` (configurable)
  - Used for: music track generation
- **YouTube Data API v3** (`google-api-python-client`)
  - OAuth 2.0 authentication
  - Used for: video uploads, thumbnail uploads

### Local Tools
- **FFmpeg** - Audio/video processing (concatenation, normalization, muxing)
- **FFprobe** - Audio metadata extraction (duration, format)

### Project Structure
```
yt-factory/
├── src/ytf/              # Main package
│   ├── cli.py            # CLI entry point (Typer)
│   ├── project.py        # Project state management (Pydantic models)
│   ├── logger.py         # Step logging utilities
│   ├── doctor.py         # Prerequisites validation
│   ├── providers/        # External API wrappers
│   │   ├── gemini.py     # Gemini API client
│   │   ├── suno.py       # Suno API client
│   │   └── youtube.py    # YouTube Data API client
│   ├── steps/            # Pipeline steps
│   │   ├── new.py        # Project creation
│   │   ├── plan.py       # Planning (Gemini)
│   │   ├── generate.py   # Music generation (Suno)
│   │   ├── review.py     # Quality control
│   │   ├── render.py      # Video rendering (FFmpeg)
│   │   ├── upload.py      # YouTube upload
│   │   └── queue.py      # Queue-based batch processing
│   └── utils/             # Utilities
│       ├── ffmpeg.py     # FFmpeg operations
│       ├── ffprobe.py    # FFprobe operations
│       ├── retry.py      # Retry/backoff utilities
│       ├── qc.py         # Quality control checks
│       └── log_summary.py # Log summary generation
├── projects/              # Project data (gitignored)
│   └── <project_id>/     # Per-project folders
│       ├── project.json  # Single source of truth
│       ├── tracks/       # Generated audio files
│       ├── assets/       # Background images, thumbnails
│       ├── output/       # Final outputs
│       └── logs/         # Step logs
└── docs/                 # Documentation
```

---

## Pipeline Architecture

### Step-Based Workflow

The pipeline consists of 6 sequential steps, each resumable:

1. **`new`** - Create project folder and `project.json` (channel-driven)
2. **`plan`** - Generate track prompts, lyrics (optional), YouTube metadata (channel-driven)
3. **`generate`** - Generate music tracks via Suno API
4. **`review`** - Quality control checks and track filtering
5. **`render`** - Concatenate tracks, normalize audio, create MP4 with per-project background/thumbnail (hard gates)
6. **`upload`** - Upload to YouTube with metadata (requires thumbnail)

### State Management

**Single Source of Truth:** `project.json`

All project state is stored in a Pydantic-validated JSON file:
- Project configuration (theme, target minutes, track count, etc.)
- Step status and error tracking
- Planning outputs (prompts, metadata)
- Generated track metadata
- Render outputs (paths, selected tracks)
- YouTube upload results

**Status Tracking:**
- `status.current_step` - Current step name
- `status.last_successful_step` - Last completed step
- `status.last_error` - Error details (step, message, stack trace, timestamp)

**Logging:**
- Each step writes to `logs/<step>.log` (text logs, always created)
- Optional JSON logs: `logs/<step>.log.json` (if `YTF_JSON_LOGS=true`)
- Error summaries: `logs/<step>_summary.json` (auto-generated after each step)
- Errors are persisted to both log file and `project.json.status.last_error`
- View logs: `ytf logs view <project_id>` or `ytf logs summary <project_id>`

---

## Current Features (Implemented)

### ✅ Project Management
- Project creation with ID generation (`YYYYMMDD_HHMMSS_<slug>`)
- Pydantic-validated project schema
- Automatic folder structure creation
- Per-step logging

### ✅ Planning (Gemini)
- Batch track prompt generation (style, title, prompt)
- Optional lyrics generation per track
- YouTube metadata generation (title, description, tags)
- Character limit validation
- JSON response parsing with markdown code block handling

### ✅ Music Generation (Suno)
- Custom mode track generation
- Instrumental and vocal modes
- Polling with exponential backoff (up to 20 minutes)
- Audio download to local `tracks/` folder
- Duration extraction via FFprobe
- Track-level error handling (failures don't stop pipeline)
- Status tracking: pending, complete, failed

### ✅ Rendering (FFmpeg)
- Track filtering (uses approved tracks or all `status=="ok"` + QC passed tracks)
- Audio concatenation via FFmpeg concat demuxer
- Loudness normalization (EBU R128 standard)
- Static background image muxing to MP4
- Background image generation via Gemini 2.5 Flash Image API
  - **Hard gate**: Each project must have its own generated background (render fails if generation fails, no upload without background)
  - Channel-aware prompts (includes channel style_guidance and intent)
- Thumbnail creation with text overlay (channel-styled)
  - Album title and channel title
  - Channel-specific fonts, layouts, colors (from brand folder if present)
  - **Hard gate**: Thumbnail required for upload (upload fails if missing)
- Chapter file generation (`chapters.txt`)
- YouTube description file generation (`youtube_description.txt`)
- Output: 1080p, 30fps MP4

### ✅ YouTube Upload
- OAuth 2.0 authentication with token caching
- Token refresh handling
- Resumable upload with exponential backoff retry (up to 10 retries)
- Metadata application (title, description, tags, privacy, category, language, made_for_kids)
- **Hard gate**: Upload requires thumbnail (`project.render.thumbnail_path` must exist)
- Thumbnail upload support (automatic if thumbnail exists)
- Idempotent behavior:
  - If video already uploaded and thumbnail uploaded: skips
  - If video already uploaded but thumbnail missing: retries thumbnail upload
- Video ID persistence to `project.json`

### ✅ Developer Tools
- `ytf doctor` - Prerequisites validation
  - FFmpeg installation check
  - Environment variables check
  - Writable projects directory check
- `ytf run <project_id>` - Run pipeline steps sequentially
- `ytf batch` - Create and run multiple projects in batch
- `ytf queue add/ls/run` - Queue-based batch processing with resumability
- `ytf logs view/summary` - View logs and error summaries

---

## Planned Features (Roadmap)

### Milestone 1: Local End-to-End Pipeline
**Status:** ✅ **COMPLETE**
- All core steps implemented and working
- One successful end-to-end run completed

### Milestone 2: Reliability + Throughput
**Status:** ✅ **COMPLETE**
- [x] Retry/backoff policy for all provider calls (Gemini, Suno, YouTube)
- [x] `approved.txt` support (manual gate for track selection)
- [x] Auto-filter bad tracks:
  - Reject too short tracks
  - Reject tracks with long initial silence
  - Reject missing/failed downloads
- [x] Batch mode (run N projects sequentially)
- [x] Queue-based batch processing (file-based queue, attempt caps, partial resume)
- [x] Improved logs (structured JSON logs optional, error summaries, `ytf logs` command)

### Milestone 3: Optional Visual Upgrades
**Status:** 📋 **PLANNED**
- [ ] Runway 10s intro slot (optional)
- [ ] Creatomate title card clip (optional)
- [ ] Enhanced thumbnail generation flow
- [ ] Consistent branding templates per channel

### Milestone 4: Server + Remote Storage
**Status:** 📋 **PLANNED**
- [ ] Docker support (optional for dev, required on server)
- [ ] StorageAdapter interface:
  - LocalStorage (default, current)
  - S3Storage (optional future)
- [ ] Server runbook (VPS setup, cron, env vars, volumes)
- [ ] Simple monitoring (failure notifications)

---

## Key Design Decisions

### 1. Local-First Architecture
- No database in v1 - all state in `project.json`
- File-based state makes debugging easy
- Can inspect/repair state manually if needed

### 2. Step-Based Pipeline
- Clear boundaries between steps
- Steps are resumable (can rerun failed step)
- Each step writes dedicated log file
- Status persisted after each step

### 3. Provider Isolation
- Providers are isolated modules
- No mixing of provider logic into rendering/uploading
- Easy to swap providers later (e.g., different LLM, music provider)

### 4. Error Handling Philosophy
- Failures must be visible
- Full stack traces persisted
- Track-level failures don't kill project
- Explicit exceptions over silent failures

### 5. Interface Design
- Interfaces defined for future extensibility:
  - `LLMProvider` (currently Gemini)
  - `MusicProvider` (currently Suno)
  - `UploadProvider` (currently YouTube)
  - `StorageAdapter` (currently LocalStorage, S3 planned)

### 6. Configuration Management
- Typed config objects (Pydantic models)
- `project.json` validated before running steps
- Environment variables for API keys and paths

---

## Configuration

### Environment Variables (`.env` file)

**Required:**
- `GEMINI_API_KEY` - Google Gemini API key
- `SUNO_API_KEY` - Suno API key
- `YOUTUBE_OAUTH_CREDENTIALS_PATH` - Path to OAuth credentials JSON file

**Optional:**
- `SUNO_MODEL` - Suno model (default: `V4_5ALL`)
- `SUNO_CALLBACK_URL` - Callback URL (default: disabled)
- `YOUTUBE_CHANNEL_TITLE` - Channel title for thumbnails (default: "Music Channel")

### Project Configuration (via CLI)

**`ytf new` command:**
- `theme` (required) - Project theme string
- `--minutes` / `-m` - Target duration in minutes (default: 60)
- `--tracks` / `-t` - Number of tracks to generate (default: 25)
- `--vocals` - Vocals mode: "on" or "off" (default: "off")
- `--lyrics` - Lyrics mode: "on" or "off" (default: "off")

**Default Settings:**
- Video: 1080p, 30fps
- Upload privacy: Unlisted
- Target length: 60 minutes

---

## Data Models

### Project Schema (Pydantic)

**Top-level fields:**
- `project_id` - Unique identifier
- `created_at` - ISO timestamp
- `theme` - Project theme
- `target_minutes` - Target duration (default: 60). Used as minimum duration for render step if less than channel minimum (allows test projects with fewer tracks)
- `track_count` - Number of tracks (default: 25)
- `vocals` - Vocals configuration (`enabled: bool`)
- `lyrics` - Lyrics configuration (`enabled: bool`, `source: "gemini" | "manual"`)
- `video` - Video settings (`width: 1920`, `height: 1080`, `fps: 30`)
- `upload` - Upload settings (`privacy: "unlisted" | "private" | "public"`)

**State:**
- `status` - Current step, last successful step, last error

**Planning:**
- `plan.prompts[]` - Track prompts with style, title, prompt, lyrics (optional)
- `plan.youtube_metadata` - Title, description, tags

**Generated Tracks:**
- `tracks[]` - Track metadata (index, prompt, job_id, audio_path, duration, status, error)

**Render:**
- `render` - Background path, thumbnail path, selected tracks, output paths

**Upload:**
- `youtube` - Video ID, uploaded timestamp, privacy, title

---

## API Integration Details

### Gemini API
- **Package:** `google-genai>=0.2.0`
- **Model:** `gemini-2.5-flash` (text), `gemini-2.5-flash-image` (images)
- **Endpoints Used:**
  - `models.generate_content()` - Text generation
  - `models.generate_content()` with `response_modalities=["IMAGE"]` - Image generation
- **Note:** Image generation requires paid Gemini API plan

### Suno API
- **Base URL:** `https://api.sunoapi.org`
- **Authentication:** Bearer token via `SUNO_API_KEY`
- **Endpoints:**
  - `POST /api/v1/generate` - Submit generation job
  - `GET /api/v1/generate/record-info?taskId=<id>` - Poll status
- **Custom Mode:** Requires `style`, `title`, and optionally `prompt` (lyrics)
- **Polling:** Exponential backoff, max 20 minutes wait
- **Variant Selection:** Suno returns 2 variants per job. System tries all variants to find one with a usable `audioUrl`, falls back to `streamAudioUrl` if `audioUrl` is empty

### YouTube Data API
- **Package:** `google-api-python-client>=2.0.0`
- **OAuth Scopes:** `https://www.googleapis.com/auth/youtube.upload`
- **Endpoints:**
  - `videos().insert()` - Upload video (resumable)
  - `thumbnails().set()` - Upload thumbnail
- **Token Caching:** Per-project `.youtube_token.json` file
- **Thumbnail Permissions:** Thumbnail upload requires YouTube account permissions. If you get HTTP 403, enable custom thumbnails in YouTube Studio or verify account permissions. The video will still upload successfully; you can set the thumbnail manually if needed.

---

## File Outputs

### Per-Project Outputs

**`tracks/`**
- `track_00.mp3`, `track_01.mp3`, ... - Generated audio files

**`assets/`**
- `background.png` - Background image (generated or default)
- `thumbnail.png` - Thumbnail with text overlay

**`output/`**
- `final.mp4` - Final rendered video (1080p, 30fps)
- `chapters.txt` - YouTube chapters file
- `youtube_description.txt` - YouTube description file

**`logs/`**
- `new.log` - Project creation log
- `plan.log` - Planning step log
- `generate.log` - Generation step log
- `render.log` - Render step log
- `upload.log` - Upload step log

---

## Usage Examples

### Basic Workflow

```bash
# 1. Create project
ytf new "fantasy tavern music" --tracks 25 --minutes 60

# 2. Plan (generate prompts and metadata)
ytf plan 20251227_163842_fantasy-tavern-music

# 3. Generate music tracks
ytf generate 20251227_163842_fantasy-tavern-music

# 4. Render final video
ytf render 20251227_163842_fantasy-tavern-music

# 5. Upload to YouTube
ytf upload 20251227_163842_fantasy-tavern-music
```

### Check Prerequisites

```bash
ytf doctor
```

---

## Development Guidelines

### Code Style
- Simple, boring code that is easy to debug
- Small modules (one file per step)
- Typed config objects (Pydantic)
- Explicit exceptions over silent failures

### Testing Strategy
- Manual testing with real projects
- Validate `project.json` structure after each step
- Check log files for errors

### Debugging
- All errors persisted to `project.json.status.last_error`
- Full stack traces in step logs
- Can manually edit `project.json` to fix state
- Can rerun failed steps without starting over

### Future Extensibility
- Provider interfaces allow swapping implementations
- StorageAdapter interface for remote storage
- Step-based architecture allows adding new steps
- No hidden state - everything in `project.json`

---

## Known Limitations

1. **No Database:** All state in `project.json` (by design for v1)
2. **No Docker:** Local development only (planned for Milestone 4)
3. **No Web UI:** CLI only (planned for later)
4. **Image Generation:** Requires paid Gemini API plan (free tier doesn't support images)
5. **Python 3.10+ Required:** CLI enforces version check (removes importlib.metadata warnings)

---

## Success Criteria

### Milestone 1 (Complete ✅)
- One command sequence produces:
  - `output/final.mp4`
  - `output/chapters.txt`
  - `output/youtube_description.txt`
  - Uploaded YouTube video ID recorded in `project.json`

### Milestone 2 (Complete ✅)
- Can run overnight batches and wake up to finished renders/uploads
- Track failures don't require manual intervention
- Auto-filtering removes obviously bad tracks
- Queue-based processing with resumability and attempt caps
- Enhanced logging and error summaries for debugging

### Milestone 3 (Planned)
- Visual enhancements plug in without changing pipeline core

### Milestone 4 (Planned)
- Pipeline runs on a server and stores outputs remotely

---

## Documentation Structure

- `00_OVERVIEW.md` - High-level overview
- `01_WORKFLOW.md` - Step-by-step workflow
- `02_ARCHITECTURE.md` - Architecture and design principles
- `03_PROJECT_SCHEMA.md` - Project JSON schema
- `04_LOGGING_AND_DEBUGGING.md` - Logging and error handling
- `05_PROVIDERS_GEMINI.md` - Gemini provider details
- `06_PROVIDERS_SUNO.md` - Suno provider details
- `07_RENDERING_FFMPEG.md` - FFmpeg rendering details
- `08_YOUTUBE_UPLOAD.md` - YouTube upload details
- `09_FUTURE_SERVER_AND_STORAGE.md` - Future server/storage plans
- `10_GUI_LATER.md` - Future GUI plans
- `ROADMAP.md` - Implementation roadmap
- `TASKS.md` - Current task list
- `DEFINITION_OF_DONE.md` - Completion criteria
- `ERRORS_AND_RECOVERY.md` - Error handling guide

---

## Current Status Summary

**✅ Completed:**
- Full local pipeline (new → plan → generate → render → upload)
- Gemini integration (planning, lyrics, metadata, background images)
- Suno integration (generation, polling, download)
- FFmpeg rendering (concatenation, normalization, muxing)
- YouTube upload (OAuth, resumable upload, metadata)
- Project state management
- Per-step logging
- Error persistence

**✅ Completed (Milestone 2):**
- Reliability improvements (retry logic, auto-filtering)
- Batch processing support (queue-based with resumability)
- Channel-driven workflow
- Quality control (review step)
- Enhanced logging (JSON logs, summaries, CLI tools)

**📋 Planned:**
- Visual enhancements (Runway, Creatomate)
- Server deployment (Docker, S3 storage)
- Web GUI

---

*Last Updated: 2025-12-27*
*Project Version: 0.1.0*

