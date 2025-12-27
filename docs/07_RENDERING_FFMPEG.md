# Rendering with FFmpeg

Rendering happens locally.

## Inputs
- background image: assets/background.png (generated with Gemini if missing)
- audio tracks: tracks/*.mp3 (or wav)

## Background Image Generation
- If `assets/background.png` doesn't exist, generates using Gemini 2.5 Flash Image API
- Prompt based on project theme for scenic, atmospheric backgrounds
- Aspect ratio: 16:9 (1920x1080)
- Falls back to default black background if Gemini generation fails

## Thumbnail Creation
- Creates `assets/thumbnail.png` with text overlay
- Overlays album title (from YouTube metadata) at top
- Overlays theme/prompt text at bottom
- White text with black outline for readability
- Same dimensions as background (1920x1080)

## Track filtering
- Use all tracks with status == "ok" and audio_path exists
- Tracks are sorted by track_index to maintain order

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
