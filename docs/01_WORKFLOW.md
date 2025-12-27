# Workflow

This is a step-based CLI pipeline.

## Setup

1. **Install Python 3.10+** (required)
2. **Create a virtual environment**:
   ```bash
   python3.10 -m venv venv
   source venv/bin/activate
   ```
3. **Install the package**:
   ```bash
   pip install -e .
   ```
4. **Verify installation**:
   ```bash
   ytf doctor
   ```

## Steps

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
- Idempotent: if `project.json.youtube.video_id` exists, skips upload

## Runner commands

### `ytf run <project_id> --to <step>`
Run pipeline steps sequentially for a project:
- Automatically determines starting point from `project.status.last_successful_step`
- Runs steps up to `--to` (default: `upload`)
- Stops immediately on failure (error persisted by step module)
- Skips upload if `project.youtube.video_id` already exists

Example:
```bash
ytf run 20251227_211203_test-channel-workflow --to render
```

### `ytf batch --channel <id> --count N --mode <mode>`
Create and run multiple projects in batch:
- Creates N projects for the specified channel
- Runs each project sequentially up to the target step
- Applies retry logic for transient errors (plan, generate, upload steps)
- Writes `projects/<batch_id>_summary.json` with per-project outcomes

Modes:
- `full`: run all steps up to upload
- `render`: run up to render
- `generate`: run up to generate
- `plan`: run up to plan
- `review`: run up to review
- `upload`: run up to upload

Example:
```bash
ytf batch --channel cafe_jazz --count 3 --mode full --theme "Evening Jazz"
```

Batch summary includes:
- Total projects, successful/failed counts
- Per-project: project_id, last_successful_step, failed_step, error_message, youtube_video_id
- Start/end timestamps

### `ytf queue` (Queue-based batch processing v2)
File-based queue system for reliable overnight runs:

**Add items to queue:**
```bash
ytf queue add --channel cafe_jazz --mode full --theme "Night Jazz" --count 3
```

**List queue status:**
```bash
ytf queue ls
```

**Process queue:**
```bash
ytf queue run [--limit N]  # Process all pending items, or limit to N
```

Queue lifecycle:
- Items start in `queue/pending/`
- Move to `queue/in_progress/` during processing
- Move to `queue/done/` on success or `queue/failed/` on failure
- Each run creates `queue/runs/<run_id>.json` and `queue/runs/<run_id>.log`

Features:
- **Partial resume**: `generate` step skips completed tracks and retries only failed tracks under attempt cap
- **Attempt caps**: Per-project and per-track attempt limits (default: 3 project attempts, 2 track attempts)
- **Idempotent**: Re-running `ytf queue run` after interruption resumes remaining items without redoing completed work
