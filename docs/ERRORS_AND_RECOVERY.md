# Errors and Recovery

Purpose:
- Make failures obvious.
- Provide a deterministic recovery path.
- Avoid redoing completed work.

Core rule:
- Never delete partial outputs on failure.
- Always persist `project.json.status.last_error` and write the full traceback to the step log.

---

## Common recovery workflow (always do this first)
1) Open `projects/<id>/project.json`
2) Check `status.last_error.step`, `status.last_error.message`
3) Open the corresponding log:
   - `logs/plan.log`
   - `logs/generate.log`
   - `logs/render.log`
   - `logs/upload.log`
4) Fix the root cause.
5) Re-run only the failed step:
   - `ytf plan <id>`
   - `ytf generate <id>`
   - `ytf render <id>`
   - `ytf upload <id>`

---

## Step: plan (Gemini) failures

### 1) Auth / missing key
Symptoms:
- 401/403 errors in `logs/plan.log`

Root causes:
- GEMINI_API_KEY missing or wrong in `.env`

Recovery:
- Fix `.env`
- Re-run `ytf plan <id>`

Prevention:
- `ytf doctor` must fail fast if GEMINI_API_KEY missing.

### 2) Rate limits / quota exceeded
Symptoms:
- 429 errors or "quota exceeded"

Recovery:
- Wait briefly, then re-run `ytf plan <id>`
- If persistent, reduce prompt count or consolidate requests.

Prevention:
- Implement retry with exponential backoff for 429/5xx.
- Prefer batching: generate all prompts in one call if feasible.

### 2b) Gemini Image Generation Quota (Render Step)
Symptoms:
- 429 RESOURCE_EXHAUSTED errors when generating background images
- Error mentions "free_tier_requests, limit: 0" for `gemini-2.5-flash-image` model
- Background falls back to default black image

Root cause:
- The free tier Gemini API plan does NOT include access to image generation models
- Image generation requires a paid Gemini API plan

Recovery:
- Upgrade your Gemini API plan at: https://ai.google.dev/pricing
- Or manually provide `assets/background.png` for each project
- The render step will use the existing background image if present

Prevention:
- Upgrade to a paid Gemini API plan before using background image generation
- Check your quota at: https://ai.dev/usage?tab=rate-limit

### 3) Low-quality or off-theme prompts
Symptoms:
- Prompts drift from theme or violate constraints.

Recovery:
- Adjust prompt template in code.
- Re-run `ytf plan <id>` with a new seed or stricter instructions.

Prevention:
- Tight variation strategy (limited degrees of freedom).
- Include explicit negative constraints:
  - no artist references
  - no modern genres if undesired
  - no brand names

### 4) Unsafe / disallowed lyric content (vocals enabled)
Symptoms:
- Lyrics contain artist references, brand names, or copied lines.

Recovery:
- Mark prompt invalid in `project.json.plan.prompts[]` and regenerate only those prompts.
- Re-run `ytf plan <id>` with stricter constraints for the invalid indices.

Prevention:
- Add a basic content check for:
  - artist-like phrases ("in the style of")
  - known brand words
  - suspiciously famous lyric fragments (simple heuristic)
- If detected: regenerate.

---

## Step: generate (Suno) failures

### 1) Auth / invalid API key
Symptoms:
- 401/403 in `logs/generate.log`

Recovery:
- Fix SUNO_API_KEY in `.env`
- Re-run `ytf generate <id>`

Prevention:
- `ytf doctor` should verify key presence.
- Log which env var is missing, never log the key value.

### 2) Job stuck in processing
Symptoms:
- Polling never reaches "completed" within timeout.
- Same status repeated for too long.

Recovery:
- Mark the track as `failed` with reason "timeout".
- Continue remaining tracks.
- Optional: re-run generate to try again for only failed tracks.

Prevention:
- Enforce timeout per job (e.g., 10-20 minutes).
- Store `attempt_count` per track and cap retries.

### 3) Download fails / file missing / 404
Symptoms:
- Job completes but download URL fails.

Recovery:
- Retry download a few times.
- If still failing, mark track failed and continue.
- Re-run generate later for failed tracks only.

Prevention:
- Separate "job complete" from "download complete".
- Persist download URL (if present) to support retries.

### 4) Audio file exists but duration read fails
Symptoms:
- duration_seconds = 0 or parsing errors.

Recovery:
- Recompute duration using ffprobe.
- If truly broken, mark track failed.

Prevention:
- Use ffprobe as canonical duration method.
- Validate: duration_seconds > 0.

### 5) Too many bad tracks
Symptoms:
- Many failures or poor quality.

Recovery:
- Increase track_count or generate additional tracks:
  - add `ytf generate <id> --extra 10` concept later
- Or introduce optional `approved.txt` gate.

Prevention:
- Keep prompts tight.
- Add simple auto-filters (silence, too short).

---

## Step: render (FFmpeg) failures

### 1) FFmpeg not installed
Symptoms:
- Command not found or `ytf render` fails immediately.

Recovery:
- Install FFmpeg (brew).
- Re-run `ytf render <id>`

Prevention:
- `ytf doctor` checks `ffmpeg -version` and `ffprobe -version`.

### 2) Background image missing
Symptoms:
- render errors: cannot open image file

Recovery:
- Place image at `assets/background.png` or update config.
- Re-run render.

Prevention:
- `ytf new` should optionally copy a default background into assets.
- Render step should fail fast with a clear message.

### 3) Unsupported audio formats
Symptoms:
- FFmpeg errors decoding input audio.

Recovery:
- Convert tracks to a standard format (wav or mp3) during generation.
- Re-run render.

Prevention:
- Standardize downloads/conversions to a single audio codec early.

### 4) Loudness normalization fails
Symptoms:
- FFmpeg loudnorm filter errors.

Recovery:
- Temporarily disable loudnorm and render without it to unblock uploads.
- Then fix loudnorm later.

Prevention:
- Keep normalization implementation simple in v1.
- Log exact FFmpeg command line.

### 5) Output MP4 has no audio or wrong duration
Symptoms:
- MP4 renders but silent, or duration mismatched.

Recovery:
- Check FFmpeg input concat list and audio mapping.
- Re-run render.

Prevention:
- After render, validate:
  - ffprobe confirms audio stream exists
  - duration roughly matches expected
  - file size non-trivial

---

## Step: upload (YouTube) failures

### 1) OAuth consent / missing credentials.json
Symptoms:
- Upload step errors early, can't start auth.

Recovery:
- Add correct OAuth client secrets file.
- Re-run upload.

Prevention:
- `ytf doctor` checks file path exists.

### 2) Token expired / revoked
Symptoms:
- 401 errors from YouTube API

Recovery:
- Delete cached token file and re-auth.
- Re-run upload.

Prevention:
- Handle token refresh automatically if library supports it.
- Log instructions when refresh fails.

### 3) Upload interrupted
Symptoms:
- network drop, partial upload, timeout

Recovery:
- Re-run `ytf upload <id>`.
- Prefer resumable upload so it continues rather than restarting.

Prevention:
- Always use resumable uploads.
- Save upload session URI if the library exposes it.

### 4) Quota exceeded
Symptoms:
- YouTube API returns quota errors.

Recovery:
- Wait until quota reset.
- Re-run upload later.

Prevention:
- Batch uploads intelligently.
- Avoid unnecessary metadata updates that consume quota.

---

## Manual intervention patterns (allowed and expected)

### Using approved.txt as a gate
When quality is inconsistent:
- Create `projects/<id>/approved.txt` listing filenames or track indices.
- Re-run `ytf render <id>` to include only approved tracks.

### Editing metadata safely
If Gemini metadata is weak:
- Edit `project.json.plan.youtube_metadata` manually.
- Re-run `ytf render <id>` to regenerate description.
- Then `ytf upload <id>`.

### Replacing background image
- Swap `assets/background.png`
- Re-run render only.

---

## Escalation checklist (when stuck)
If you hit repeated failures:
- Confirm `ytf doctor` passes.
- Inspect the exact HTTP error response in logs.
- Reduce scope:
  - fewer tracks
  - shorter target minutes
  - disable vocals
- Validate each step independently before chaining.

When asking an LLM for help:
- paste only the relevant log section
- include the step name and the exact error line
- include the last successful step and the command you ran
