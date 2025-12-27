"""
New step: Create a new project with folder structure and project.json.

This is the first step in the pipeline. It creates the project folder,
initializes project.json with user inputs, and sets up required directories.
"""

from datetime import datetime

from ytf.logger import StepLogger
from ytf.project import (
    Project,
    VocalsConfig,
    LyricsConfig,
    VideoConfig,
    UploadConfig,
    ProjectStatus,
    generate_project_id,
    create_project_folder,
    save_project,
    update_status,
)


def create_project(
    theme: str,
    minutes: int = 60,
    tracks: int = 25,
    vocals: str = "off",
    lyrics: str = "off",
) -> str:
    """
    Create a new project with folder structure and project.json.

    Args:
        theme: Project theme
        minutes: Target duration in minutes (default 60)
        tracks: Number of tracks to generate (default 25)
        vocals: "on" or "off" (default "off")
        lyrics: "on" or "off" (default "off", only applies if vocals is "on")

    Returns:
        Project ID string
    """
    # Generate project ID
    project_id = generate_project_id(theme)

    # Create folder structure
    project_dir = create_project_folder(project_id)

    # Initialize project with user inputs
    vocals_enabled = vocals == "on"
    lyrics_enabled = lyrics == "on" and vocals_enabled

    project = Project(
        project_id=project_id,
        created_at=datetime.now().isoformat(),
        theme=theme,
        target_minutes=minutes,
        track_count=tracks,
        vocals=VocalsConfig(enabled=vocals_enabled),
        lyrics=LyricsConfig(enabled=lyrics_enabled, source="gemini"),
        video=VideoConfig(width=1920, height=1080, fps=30),
        upload=UploadConfig(privacy="unlisted"),
        status=ProjectStatus(current_step="new", last_successful_step="new"),
    )

    # Use logger for this step
    with StepLogger(project_id, "new") as log:
        try:
            log.info(f"Creating project: {project_id}")
            log.info(f"Theme: {theme}")
            log.info(f"Target minutes: {minutes}")
            log.info(f"Track count: {tracks}")
            log.info(f"Vocals: {vocals_enabled}")
            log.info(f"Lyrics: {lyrics_enabled}")

            # Save project.json
            save_project(project)
            update_status(project, "new", error=None)
            save_project(project)

            log.info(f"Project created successfully: {project_dir}")
        except Exception as e:
            update_status(project, "new", error=e)
            save_project(project)
            log.error(f"Failed to create project: {e}")
            raise

    return project_id

