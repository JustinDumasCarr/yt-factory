# Logging and debugging

Goal: when something fails, you know exactly where and why.

## Log files per step
- logs/plan.log
- logs/generate.log
- logs/render.log
- logs/upload.log

Each log line should include:
- timestamp
- step
- project_id
- track_index (if relevant)
- message
- error details when present

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
3. Open corresponding log file.
4. Re-run only the failed step.

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
