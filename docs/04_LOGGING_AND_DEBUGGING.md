# Logging and debugging

Goal: when something fails, you know exactly where and why.

## Log files per step
- logs/plan.log (text log, always created)
- logs/plan.log.json (JSON log, optional, created if YTF_JSON_LOGS=true)
- logs/plan_summary.json (error summary, auto-generated after step completes)
- Same pattern for generate, review, render, upload steps

### Text logs (default)
Each log line includes:
- timestamp
- step
- level (INFO, WARNING, ERROR)
- message
- context metadata (track_index, provider, retry_count, duration_ms) when relevant

### JSON logs (optional)
Enable with environment variable: `YTF_JSON_LOGS=true`

JSON log entries are structured:
```json
{
  "timestamp": "2025-12-27T10:30:45.123456",
  "step": "plan",
  "level": "INFO",
  "message": "Generating track prompts",
  "project_id": "20251227_103045_theme",
  "track_index": 0,
  "provider": "gemini",
  "duration_ms": 1234
}
```

### Error summaries
After each step completes (success or failure), a summary is automatically generated:
- `logs/<step>_summary.json` contains:
  - Error counts by type (auth, rate_limit, timeout, validation, ffmpeg, unknown)
  - Error counts by provider (gemini, suno, youtube)
  - Retry statistics
  - Duration breakdown (total, average, min, max, by provider)
  - Track-level failures (for generate step)

## status.json or status section in project.json
Record:
- current_step
- last_successful_step
- last_error with:
  - step, message, stack, at (timestamp)
  - kind: Error category (auth, rate_limit, timeout, provider_http, validation, ffmpeg, unknown)
  - provider: Provider name (gemini, suno, youtube) or null
  - raw: Raw error details from provider (truncated if >2000 chars)

## Debug workflow
1. Open project folder.
2. Check `project.json.status.last_error`.
3. View logs using `ytf logs` command (see below) or open log file directly.
4. Check error summary: `ytf logs summary <project_id> [--step <step>]`
5. Re-run only the failed step.

## Viewing logs with CLI

### View log entries
```bash
# View recent log entries (last 50 lines)
ytf logs view <project_id>

# View logs for specific step
ytf logs view <project_id> --step plan

# View only errors
ytf logs view <project_id> --errors-only

# View JSON logs (if enabled)
ytf logs view <project_id> --json

# View more lines
ytf logs view <project_id> --lines 100
```

### View error summaries
```bash
# View summary for all steps
ytf logs summary <project_id>

# View summary for specific step
ytf logs summary <project_id> --step generate
```

Summaries show:
- Error counts by type and provider
- Retry statistics
- Duration breakdown
- Track failures (for generate step)

## Retry strategy
- Provider calls now have automatic retries:
  - Gemini: 3 retries with exponential backoff + jitter for 429/5xx/timeouts
  - Suno: 3 retries for API calls (generate, status check, download)
  - YouTube: Up to 10 retries for resumable uploads (includes 429)
  - All retries use exponential backoff with jitter
  - Non-retriable errors (auth, validation) fail fast
- Retry attempts are logged with `[RETRY]` prefix in step logs.
- Track-level failures do not kill the project.
- Final failures always include raw error details in `last_error.raw` for debugging.
