"""
Upload step: Upload to YouTube using YouTube Data API v3.

Handles OAuth authentication, resumable uploads, metadata application,
and thumbnail upload.
"""

from datetime import datetime
from pathlib import Path

from ytf.logger import StepLogger
from ytf.project import (
    PROJECTS_DIR,
    YouTubeData,
    load_project,
    save_project,
    update_status,
)
from ytf.providers.youtube import YouTubeProvider


def run(project_id: str) -> None:
    """
    Run the upload step.

    Args:
        project_id: Project ID

    Raises:
        Exception: If step fails (error persisted to project.json)
    """
    project = load_project(project_id)
    project_dir = PROJECTS_DIR / project_id

    with StepLogger(project_id, "upload") as log:
        try:
            update_status(project, "upload")
            save_project(project)

            log.info("Starting YouTube upload step")

            # Validate prerequisites
            if not project.render or not project.render.output_mp4_path:
                raise RuntimeError(
                    "Render step must be completed before upload. "
                    "No output video found."
                )

            if not project.plan or not project.plan.youtube_metadata:
                raise RuntimeError(
                    "Plan step must be completed before upload. "
                    "No YouTube metadata found."
                )

            # Initialize YouTube provider
            log.info("Initializing YouTube provider...")
            provider = YouTubeProvider(project_id)

            # Prepare video file path
            video_path = project_dir / project.render.output_mp4_path
            if not video_path.exists():
                raise FileNotFoundError(
                    f"Video file not found: {video_path}. "
                    "Please run render step first."
                )

            log.info(f"Video file: {video_path}")

            # Prepare metadata
            metadata = project.plan.youtube_metadata
            title = metadata.title
            tags = metadata.tags

            # Read description from file if available
            description = metadata.description
            if project.render.description_path:
                description_path = project_dir / project.render.description_path
                if description_path.exists():
                    description = description_path.read_text(encoding="utf-8")
                    log.info(f"Using description from {description_path}")
                else:
                    log.warning(
                        f"Description file not found: {description_path}, "
                        "using metadata description"
                    )

            # Get privacy status (default: unlisted)
            privacy = project.upload.privacy if project.upload else "unlisted"

            log.info(f"Uploading video: {title}")
            log.info(f"Privacy: {privacy}")
            log.info(f"Tags: {', '.join(tags) if tags else 'None'}")

            # Upload video
            log.info("Starting resumable upload...")
            response = provider.upload_video(
                video_path=video_path,
                title=title,
                description=description,
                tags=tags,
                privacy_status=privacy,
                category_id="10",  # Music category
            )

            video_id = response["id"]
            log.info(f"Video uploaded successfully! Video ID: {video_id}")

            # Upload thumbnail if available
            if project.render.thumbnail_path:
                thumbnail_path = project_dir / project.render.thumbnail_path
                if thumbnail_path.exists():
                    log.info(f"Uploading custom thumbnail: {thumbnail_path}")
                    try:
                        provider.upload_thumbnail(video_id, thumbnail_path)
                        log.info("Thumbnail uploaded successfully")
                    except Exception as e:
                        log.warning(f"Failed to upload thumbnail: {e}")
                        log.info("Continuing without custom thumbnail...")
                else:
                    log.warning(
                        f"Thumbnail file not found: {thumbnail_path}, "
                        "skipping thumbnail upload"
                    )

            # Persist YouTube data to project.json
            project.youtube = YouTubeData(
                video_id=video_id,
                uploaded_at=datetime.now().isoformat(),
                privacy=privacy,
                title=title,
            )
            update_status(project, "upload", error=None)
            save_project(project)

            log.info("Upload step completed successfully")
            log.info(f"YouTube video URL: https://www.youtube.com/watch?v={video_id}")

        except Exception as e:
            update_status(project, "upload", error=e)
            save_project(project)
            log.error(f"Upload step failed: {e}")
            raise

