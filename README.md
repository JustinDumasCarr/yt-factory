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

## Requirements

- Python **3.10 or higher** (required)
  - Python 3.9 is not supported due to dependency requirements
  - The `importlib.metadata.packages_distributions` error on Python 3.9 is expected and will be resolved by using Python 3.10+
- FFmpeg and FFprobe installed
- API keys for Gemini, Suno, and YouTube OAuth credentials

**Note**: On macOS with system Python, you may see urllib3/LibreSSL warnings. These are harmless and can be ignored. For a clean environment, use Python 3.10+ from Homebrew or pyenv.

## Installation

1. **Create a virtual environment** (recommended):
   ```bash
   python3.10 -m venv venv
   source venv/bin/activate  # On macOS/Linux
   ```

2. **Install the package in editable mode**:
   ```bash
   pip install -e .
   ```

   This installs `ytf` as a command-line tool and makes the package editable for development.

3. **Verify installation**:
   ```bash
   ytf --help
   # or
   python -m ytf --help
   ```

4. **Set up environment variables**:
   - Copy `.env.example` to `.env` (if it exists)
   - Add your API keys:
     - `GEMINI_API_KEY`
     - `SUNO_API_KEY`
     - `YOUTUBE_OAUTH_CREDENTIALS_PATH` (path to OAuth credentials JSON)

5. **Run prerequisite checks**:
   ```bash
   ytf doctor
   ```

   This verifies FFmpeg, FFprobe, and environment variables are set up correctly.

## Quickstart

1. **Create a new project**:
   ```bash
   ytf new "My Theme" --channel cafe_jazz
   ```

2. **Run the pipeline**:
   ```bash
   ytf run <project_id>  # Runs all steps: plan -> generate -> review -> render -> upload
   ```

   Or run steps individually:
   ```bash
   ytf plan <project_id>
   ytf generate <project_id>
   ytf review <project_id>
   ytf render <project_id>
   ytf upload <project_id>
   ```

3. **Check project status**:
   - View `projects/<project_id>/project.json` for current state
   - Check `projects/<project_id>/logs/` for step logs

## Documentation

Docs live in `docs/`.
Start with `AGENTS.md`, then `docs/00_OVERVIEW.md` and `docs/01_WORKFLOW.md`.
