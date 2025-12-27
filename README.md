# yt-factory

Local-first automation pipeline to generate music compilations and upload to YouTube.

Primary goals:
- Run locally on macOS first.
- Simple CLI workflow with clear logs and resumable steps.
- Use Gemini for planning and lyrics (optional).
- Use Gemini for background image generation (requires paid API plan).
- Use Suno for music generation using an API key.
- Render final MP4 locally with FFmpeg.
- Upload via YouTube Data API using OAuth.
- Easy upgrade path to server runs, Docker, and remote storage later.
- Optional GUI later without rewriting the pipeline.

**Note**: Background image generation requires a paid Gemini API plan. The free tier does not include access to image generation models. See `.env.example` and `docs/07_RENDERING_FFMPEG.md` for details.

## Quickstart
1. Install FFmpeg.
2. Create a `.env` file with required keys.
3. Create a new project folder.
4. Run steps in order: plan. generate. render. upload.

Docs live in `docs/`.
Start with `docs/00_OVERVIEW.md` and `docs/01_WORKFLOW.md`.
