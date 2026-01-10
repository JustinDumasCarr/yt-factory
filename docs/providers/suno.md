# Suno provider

Suno is used to generate tracks from prompts.

## Requirements
- Suno API key in `.env`.
- Provider wrapper should be isolated behind MusicProvider interface.

## Core behaviors
- submit generation job per prompt
- poll for completion
- download audio file (tries all variants, falls back to streamAudioUrl if audioUrl is empty)
- store job_id and audio_path in project.json

## Variant handling
Suno returns **2 variants per generation job**. The generate step:
- Downloads and persists **both variants** from each job
- Each variant gets a distinct title: base title + " I" or " II" (e.g., "Whispering Scrolls I" and "Whispering Scrolls II")
- Prefers `audioUrl`, falls back to `streamAudioUrl` if `audioUrl` is empty
- Both variants are stored as separate `Track` entries in `project.json` with:
  - `job_index`: Which planned job this came from
  - `variant_index`: 0 or 1 (which variant from the job)
  - `title`: Variant-specific title with suffix
  - `style`: Music style (shared from the job prompt)
- Resume logic: If one variant exists but the other is missing, re-polls and downloads the missing variant without starting a new job

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
