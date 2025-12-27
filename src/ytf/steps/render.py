"""
Render step: Render final video using FFmpeg.

Concatenates all available tracks, normalizes audio, and creates MP4 with static background.
"""

import subprocess
from pathlib import Path

from ytf.logger import StepLogger
from ytf.project import PROJECTS_DIR, RenderData, load_project, save_project, update_status
from ytf.utils import ffmpeg


def format_timestamp(seconds: float) -> str:
    """
    Format seconds as YouTube chapter timestamp (MM:SS or HH:MM:SS).

    Args:
        seconds: Duration in seconds

    Returns:
        Formatted timestamp string
    """
    total_seconds = int(seconds)
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    secs = total_seconds % 60

    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def run(project_id: str) -> None:
    """
    Run the render step.

    Args:
        project_id: Project ID

    Raises:
        Exception: If step fails (error persisted to project.json)
    """
    project = load_project(project_id)
    project_dir = PROJECTS_DIR / project_id

    with StepLogger(project_id, "render") as log:
        try:
            update_status(project, "render")
            save_project(project)

            log.info("Starting render step")

            # Validate FFmpeg is available
            if not ffmpeg.check_ffmpeg():
                raise RuntimeError("FFmpeg is not available. Run 'ytf doctor' to check prerequisites.")

            # Filter tracks: only status == "ok" and audio_path exists
            available_tracks = [
                track
                for track in project.tracks
                if track.status == "ok" and track.audio_path is not None
            ]

            if not available_tracks:
                raise RuntimeError("No available tracks to render. All tracks are failed or missing audio files.")

            # Sort by track_index to maintain order
            available_tracks.sort(key=lambda t: t.track_index)

            log.info(f"Found {len(available_tracks)} available tracks")
            total_duration = sum(track.duration_seconds for track in available_tracks)
            log.info(f"Total duration: {format_timestamp(total_duration)} ({total_duration:.2f} seconds)")

            # Get track indices for persistence
            selected_indices = [track.track_index for track in available_tracks]

            # Prepare paths
            tracks_dir = project_dir / "tracks"
            output_dir = project_dir / "output"
            assets_dir = project_dir / "assets"
            output_dir.mkdir(exist_ok=True)

            # Step 1: Concatenate audio files
            log.info("Concatenating audio tracks...")
            concat_audio_path = output_dir / "concat_audio.mp3"
            audio_file_paths = [
                project_dir / track.audio_path
                for track in available_tracks
            ]
            ffmpeg.concatenate_audio_files(audio_file_paths, concat_audio_path)
            log.info(f"Concatenated audio saved to {concat_audio_path}")

            # Step 2: Normalize loudness
            log.info("Normalizing audio loudness...")
            normalized_audio_path = output_dir / "normalized_audio.mp3"
            ffmpeg.normalize_loudness(concat_audio_path, normalized_audio_path)
            log.info(f"Normalized audio saved to {normalized_audio_path}")

            # Step 3: Handle background image
            background_path = assets_dir / "background.png"
            if not background_path.exists():
                log.info("Background image not found, generating default...")
                ffmpeg.generate_default_background(
                    background_path,
                    width=project.video.width,
                    height=project.video.height,
                )
                log.info(f"Generated default background at {background_path}")
            else:
                log.info(f"Using existing background image at {background_path}")

            # Step 4: Create video
            log.info("Creating video with static background...")
            final_video_path = output_dir / "final.mp4"
            ffmpeg.create_video_from_image_and_audio(
                background_path,
                normalized_audio_path,
                final_video_path,
                width=project.video.width,
                height=project.video.height,
                fps=project.video.fps,
            )
            log.info(f"Final video saved to {final_video_path}")

            # Step 5: Generate chapters
            log.info("Generating chapters...")
            chapters_path = output_dir / "chapters.txt"
            chapters_lines = []
            cumulative_time = 0.0

            # Create a lookup for track titles from plan.prompts
            prompt_lookup = {}
            if project.plan and project.plan.prompts:
                for prompt in project.plan.prompts:
                    prompt_lookup[prompt.track_index] = prompt.title

            for track in available_tracks:
                timestamp = format_timestamp(cumulative_time)
                # Use title from plan if available, otherwise use track index
                title = prompt_lookup.get(track.track_index, f"Track {track.track_index + 1}")
                chapters_lines.append(f"{timestamp} {title}")
                cumulative_time += track.duration_seconds

            with open(chapters_path, "w", encoding="utf-8") as f:
                f.write("\n".join(chapters_lines))
                f.write("\n")

            log.info(f"Chapters saved to {chapters_path}")

            # Step 6: Generate YouTube description
            log.info("Generating YouTube description...")
            description_path = output_dir / "youtube_description.txt"

            # Start with metadata description if available
            description_lines = []
            if project.plan and project.plan.youtube_metadata:
                description_lines.append(project.plan.youtube_metadata.description)
            else:
                description_lines.append("Music compilation")

            # Append chapters section
            description_lines.append("")
            description_lines.append("Chapters:")
            description_lines.extend(chapters_lines)

            with open(description_path, "w", encoding="utf-8") as f:
                f.write("\n".join(description_lines))
                f.write("\n")

            log.info(f"YouTube description saved to {description_path}")

            # Step 7: Persist render data to project.json
            project.render = RenderData(
                background_path=str(background_path.relative_to(project_dir)),
                selected_track_indices=selected_indices,
                output_mp4_path=str(final_video_path.relative_to(project_dir)),
                chapters_path=str(chapters_path.relative_to(project_dir)),
                description_path=str(description_path.relative_to(project_dir)),
            )

            # Clean up intermediate files
            log.info("Cleaning up intermediate files...")
            if concat_audio_path.exists():
                concat_audio_path.unlink()
            if normalized_audio_path.exists():
                normalized_audio_path.unlink()

            # Mark as successful
            update_status(project, "render", error=None)
            save_project(project)

            log.info("Render step completed successfully")
            log.info(f"Output files:")
            log.info(f"  - Video: {final_video_path}")
            log.info(f"  - Chapters: {chapters_path}")
            log.info(f"  - Description: {description_path}")

        except Exception as e:
            update_status(project, "render", error=e)
            save_project(project)
            log.error(f"Render step failed: {e}")
            raise
