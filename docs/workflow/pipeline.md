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
- **Job prompts** for Suno (count = `ceil(track_count/2)` since each job produces 2 variants)
  - Applies channel constraints: banned terms, style guidance, energy level
  - Each prompt has a `job_index` (0-based)
- Optional lyrics for each job if vocals are on
- YouTube metadata draft: title, description, tags (validated against channel tag rules)
- Chooses CTA variant from channel profile and persists to `project.funnel.cta_variant_id`
Writes into `project.json` under `plan`.

### 3) Generate (Suno)
For each job prompt:
- submit one generation job
- poll until ready (Suno returns 2 variants per job)
- download **both variants** as separate audio files
- assign sequential `track_index` (job 0 → tracks 0,1; job 1 → tracks 2,3; etc.)
- create titles: base title + " I" for variant 0, base title + " II" for variant 1
- compute duration for each variant
- write 2 `Track` entries per job into `project.json.tracks[]`

Variant handling:
- Both variants are downloaded and persisted (not just one)
- Prefers `audioUrl`, falls back to `streamAudioUrl` if `audioUrl` is empty
- Each variant gets: `job_index`, `variant_index` (0 or 1), `title` (with suffix), `style`

Failure policy:
- if one variant fails, continue with the other variant
- if entire job fails, mark both variants as failed
- record error per variant

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
- Duration validation:
  - Checks total duration against channel minimum (`channel.duration_rules.min_minutes`)
  - **Override**: If `project.target_minutes` is set and is less than channel minimum, uses `project.target_minutes` as the minimum instead
    - This allows test projects with fewer tracks to render successfully
  - Fail fast if total duration is below the effective minimum (channel or project override)
  - Warns if total duration is below channel target (but above minimum)

Process:
- Background image policy (hard gate):
  - Every project must have its own generated background at `projects/<project_id>/assets/background.png`.
  - If it does not exist, the render step generates it with Gemini using channel-aware prompt guidance.
  - If background generation fails, render fails (no upload) so you can re-run render once assets are available.
- concatenate audio tracks until target length reached
- normalize loudness
- Create thumbnail with channel-specific styling:
  - Uses `channel.thumbnail_style` (font, layout, colors)
  - Custom font from `assets/brand/<channel_id>/font.ttf` if present
  - Sanitizes title if it contains `safe_words`
  - **Hard gate**: if thumbnail generation fails, render fails (no upload)
- mux static image + audio into final MP4

Outputs:
- `output/final.mp4`
- `output/chapters.txt`
- `output/youtube_description.txt` (templated with channel description + CTA)
- `output/pinned_comment.txt` (short + long CTA variants)
- `assets/thumbnail.png` (channel-styled thumbnail)

### 6) Upload (YouTube Data API)
- OAuth auth flow, token cached locally
- resumable upload
- apply metadata and upload settings
- record returned video ID in `project.json`
- **Hard gate**: upload will not proceed without a generated thumbnail (`project.render.thumbnail_path` must exist on disk)
- Idempotent:
  - if `project.json.youtube.video_id` exists and thumbnail already uploaded, skips
  - if `project.json.youtube.video_id` exists but thumbnail not uploaded, retries thumbnail upload
- **Note**: Thumbnail upload requires YouTube account permissions. If you get HTTP 403, enable custom thumbnails in YouTube Studio or verify account permissions. The video will still upload successfully; you can set the thumbnail manually if needed.

## Common Commands (Quick Reference)

**Single project execution:**
```bash
ytf run <project_id> [--to <step>]  # Run pipeline steps sequentially
```

**Queue-based batch processing:**
```bash
ytf queue add --channel <id> --theme <theme> --mode full --count N  # Add items to queue
ytf queue ls                                                         # List queue status
ytf queue run [--limit N]                                           # Process queue items
```

**View logs and summaries:**
```bash
ytf logs view <project_id> [--step <step>] [--errors-only] [--json]  # View log entries
ytf logs summary <project_id> [--step <step>]                        # View error summaries
```

**Individual step commands:**
```bash
ytf new <theme> --channel <id>     # Create project
ytf plan <project_id>               # Generate planning data
ytf generate <project_id>           # Generate music tracks
ytf review <project_id>             # Run quality control
ytf render <project_id>             # Render final video
ytf upload <project_id>             # Upload to YouTube
```

---

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
- **Enhanced summaries**: Queue run summaries include aggregated error statistics (by type, provider, step), retry counts, and per-project log summaries

### `ytf logs` (View logs and summaries)
View project logs and error summaries:

**View log entries:**
```bash
# View recent log entries (last 50 lines)
ytf logs view <project_id>

# View logs for specific step
ytf logs view <project_id> --step plan

# View only errors
ytf logs view <project_id> --errors-only

# View JSON logs (if YTF_JSON_LOGS=true)
ytf logs view <project_id> --json
```

**View error summaries:**
```bash
# View summary for all steps
ytf logs summary <project_id>

# View summary for specific step
ytf logs summary <project_id> --step generate
```

Summaries show error counts by type/provider, retry statistics, duration breakdown, and track failures.
- **Idempotent**: Re-running `ytf queue run` after interruption resumes remaining items without redoing completed work
