"""
New step: Create a new project with folder structure and project.json.

This is the first step in the pipeline. It creates the project folder,
initializes project.json with user inputs, and sets up required directories.
"""

from datetime import datetime
from typing import Optional

from ytf.channel import get_channel
from ytf.logger import StepLogger
from ytf.project import (
    Project,
    VocalsConfig,
    LyricsConfig,
    VideoConfig,
    UploadConfig,
    FunnelConfig,
    ProjectStatus,
    generate_project_id,
    create_project_folder,
    save_project,
    update_status,
)


def create_project(
    theme: str,
    channel_id: str,
    minutes: Optional[int] = None,
    tracks: Optional[int] = None,
    vocals: str = "off",
    lyrics: str = "off",
) -> str:
    """
    Create a new project with folder structure and project.json.

    Args:
        theme: Project theme
        channel_id: Channel ID (e.g., "cafe_jazz", "fantasy_tavern")
        minutes: Target duration in minutes (overrides channel default if provided)
        tracks: Number of tracks to generate (overrides channel default if provided)
        vocals: "on" or "off" (default "off")
        lyrics: "on" or "off" (default "off", only applies if vocals is "on")

    Returns:
        Project ID string

    Raises:
        FileNotFoundError: If channel config doesn't exist
        ValueError: If channel config is invalid
    """
    # Load channel profile
    channel = get_channel(channel_id)

    # Generate project ID
    project_id = generate_project_id(theme)

    # Create folder structure
    project_dir = create_project_folder(project_id)

    # Use channel defaults, but allow overrides
    target_minutes = minutes if minutes is not None else channel.duration_rules.target_minutes
    track_count = tracks if tracks is not None else channel.duration_rules.track_count

    # Initialize project with user inputs and channel defaults
    vocals_enabled = vocals == "on"
    lyrics_enabled = lyrics == "on" and vocals_enabled

    # Use channel prompt constraints if vocals not explicitly set
    if vocals == "off":
        # Channel default takes precedence
        vocals_enabled = not channel.prompt_constraints.default_instrumental

    project = Project(
        project_id=project_id,
        created_at=datetime.now().isoformat(),
        theme=theme,
        channel_id=channel_id,
        intent=channel.intent,
        target_minutes=target_minutes,
        track_count=track_count,
        vocals=VocalsConfig(enabled=vocals_enabled),
        lyrics=LyricsConfig(enabled=lyrics_enabled, source="gemini"),
        video=VideoConfig(width=1920, height=1080, fps=30),
        upload=UploadConfig(privacy=channel.upload_defaults.privacy),
        funnel=FunnelConfig(),
        status=ProjectStatus(current_step="new", last_successful_step="new"),
    )

    # Use logger for this step
    with StepLogger(project_id, "new") as log:
        try:
            log.info(f"Creating project: {project_id}")
            log.info(f"Channel: {channel_id} ({channel.name})")
            log.info(f"Theme: {theme}")
            log.info(f"Intent: {channel.intent}")
            log.info(f"Target minutes: {target_minutes} (channel default: {channel.duration_rules.target_minutes})")
            log.info(f"Track count: {track_count} (channel default: {channel.duration_rules.track_count})")
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

