# Rendering with FFmpeg

Rendering happens locally.

## Inputs
- background image: assets/background.png (default)
- audio tracks: tracks/*.mp3 (or wav)
- target_minutes: 60

## Selection logic (v1)
- if approved.txt exists, use only approved tracks
- else use all ok tracks
- stop adding tracks when target length reached

## Audio processing
- concatenate tracks
- loudness normalization for consistent volume
- optional fade between tracks can be added later

## Video processing
- static background image
- 1080p 30fps
- mux with final audio into MP4

## Outputs
- output/final.mp4
- output/chapters.txt
- output/youtube_description.txt
