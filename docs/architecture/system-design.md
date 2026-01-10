# Architecture

## Design principles
- Local-first. File-based state.
- Clear step boundaries.
- No database in v1.
- Minimal moving parts.
- Observable failures.

## Modules
- CLI entrypoint
- Project state manager (read/write `project.json`)
- Providers
  - LLMProvider: Gemini
  - MusicProvider: Suno
  - UploadProvider: YouTube
- Renderer: FFmpeg

## Interfaces to keep stable
### LLMProvider
- plan_project(project) -> plan data
- generate_lyrics(track_prompt) -> lyrics

### MusicProvider
- create_track(prompt, options) -> job_id
- poll(job_id) -> status
- download(job_id) -> local audio path

### Renderer
- render(project) -> output paths

### UploadProvider
- upload_video(project, mp4_path, metadata) -> youtube_video_id

## Storage adapter (future)
In v1, storage is local filesystem.
Future uses StorageAdapter:
- read(path)
- write(path, bytes)
- list(prefix)
- exists(path)

LocalStorage is default.
S3Storage later.
