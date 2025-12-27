# Rendering with FFmpeg

Rendering happens locally.

## Inputs
- background image: assets/background.png (default, generated if missing)
- audio tracks: tracks/*.mp3 (or wav)

## Track filtering
- Use all tracks with status == "ok" and audio_path exists
- Tracks are sorted by track_index to maintain order

## Audio processing
- concatenate all available tracks
- loudness normalization for consistent volume (I=-16 LUFS, YouTube standard)
- optional fade between tracks can be added later

## Video processing
- static background image
- 1080p 30fps
- mux with final audio into MP4

## Outputs
- output/final.mp4
- output/chapters.txt
- output/youtube_description.txt
