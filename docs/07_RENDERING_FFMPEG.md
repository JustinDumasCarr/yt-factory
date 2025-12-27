# Rendering with FFmpeg

Rendering happens locally.

## Inputs
- background image: assets/background.png (generated with Gemini if missing)
- audio tracks: tracks/*.mp3 (or wav)

## Background Image Generation
- If `assets/background.png` doesn't exist, generates using Gemini 2.5 Flash Image API
- **IMPORTANT**: Requires a PAID Gemini API plan. The free tier does not include access to `gemini-2.5-flash-image` model.
- Upgrade your plan at: https://ai.google.dev/pricing
- Prompt based on project theme for scenic, atmospheric backgrounds
- Aspect ratio: 16:9 (1920x1080)
- **Hard gate**: if Gemini generation fails, render fails (no upload) so you can retry later

## Thumbnail Creation
- Creates `assets/thumbnail.png` with text overlay
- Overlays album title (from YouTube metadata) at top
- Overlays theme/prompt text at bottom
- White text with black outline for readability
- Same dimensions as background (1920x1080)
- **Hard gate**: if thumbnail creation fails, render fails (no upload)

## Track filtering
- Use all tracks with status == "ok" and audio_path exists
- Tracks are sorted by track_index to maintain order

## Duration validation
- Checks total duration against channel minimum (`channel.duration_rules.min_minutes`)
- **Override**: If `project.target_minutes` is set and is less than channel minimum, uses `project.target_minutes` as the minimum instead
  - This allows test projects with fewer tracks to render successfully
  - Example: Channel requires 90 min minimum, but test project with 2 tracks (9 min) can still render if `project.target_minutes=9`
- Fails fast if total duration is below the effective minimum (channel or project override)
- Warns if total duration is below channel target (but above minimum)

## Audio processing
- concatenate all available tracks
- loudness normalization for consistent volume (I=-16 LUFS, YouTube standard)
- optional fade between tracks can be added later

## Video processing
- static background image (generated or existing)
- 1080p 30fps
- mux with final audio into MP4

## Outputs
- output/final.mp4
- output/chapters.txt
- output/youtube_description.txt
- assets/background.png (generated background image)
- assets/thumbnail.png (thumbnail with text overlay)
