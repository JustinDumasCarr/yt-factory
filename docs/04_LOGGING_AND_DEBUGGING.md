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
- last_error with stack trace

## Debug workflow
1. Open project folder.
2. Check `project.json.status.last_error`.
3. Open corresponding log file.
4. Re-run only the failed step.

## Retry strategy
- Provider calls should have:
  - timeouts
  - bounded retries
  - exponential backoff
- Track-level failures do not kill the project.
