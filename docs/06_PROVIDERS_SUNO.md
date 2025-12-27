# Suno provider

Suno is used to generate tracks from prompts.

## Requirements
- Suno API key in `.env`.
- Provider wrapper should be isolated behind MusicProvider interface.

## Core behaviors
- submit generation job per prompt
- poll for completion
- download audio file
- store job_id and audio_path in project.json

## Failure handling
- record per-track failures
- continue generating remaining tracks
- capture raw API error response for debugging

## Track ordering
Order is by track_index.
Optional manual override:
- `approved.txt` listing tracks or filenames

## Notes
Keep this provider thin.
Do not mix rendering logic into the provider.
