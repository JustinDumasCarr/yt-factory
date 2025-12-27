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

            # If already uploaded, still allow retrying thumbnail upload.
            if project.youtube and project.youtube.video_id:
                video_id = project.youtube.video_id
                if project.youtube.thumbnail_uploaded:
                    log.info(
                        f"Video already uploaded and thumbnail uploaded. Video ID: {video_id}. "
                        f"URL: https://www.youtube.com/watch?v={video_id}. "
                        "Skipping upload step."
                    )
                    update_status(project, "upload", error=None)
                    save_project(project)
                    return

                log.info(
                    f"Video already uploaded (Video ID: {video_id}) but thumbnail not uploaded yet. "
                    "Will attempt thumbnail upload."
                )

                # Validate prerequisites for thumbnail upload
                if not project.render or not project.render.thumbnail_path:
                    raise RuntimeError(
                        "Render step must generate a thumbnail before upload. "
                        "No thumbnail path found in project.render."
                    )

                thumbnail_path = project_dir / project.render.thumbnail_path
                if not thumbnail_path.exists():
                    raise FileNotFoundError(
                        f"Thumbnail file not found: {thumbnail_path}. "
                        "Please re-run render to generate it."
                    )

                provider = YouTubeProvider(project_id)
                log.info(f"Uploading custom thumbnail: {thumbnail_path.resolve()}")
                provider.upload_thumbnail(video_id, thumbnail_path)
                log.info("Thumbnail uploaded successfully")

                # Persist updated YouTube data
                project.youtube.thumbnail_uploaded = True
                project.youtube.thumbnail_path = str(project.render.thumbnail_path)
                update_status(project, "upload", error=None)
                save_project(project)
                return

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

            log.info(f"Video file: {video_path.resolve()}")

            # Prepare metadata
            metadata = project.plan.youtube_metadata
            title = metadata.title
            tags = metadata.tags

            # Read description from file if available
            description = metadata.description
            description_path = None
            if project.render.description_path:
                description_path = project_dir / project.render.description_path
                if description_path.exists():
                    description = description_path.read_text(encoding="utf-8")
                    log.info(f"Using description from: {description_path.resolve()}")
                else:
                    log.warning(
                        f"Description file not found: {description_path}, "
                        "using metadata description"
                    )
            else:
                log.info("No description file path in render data, using metadata description")

            # Get upload settings from project (channel-driven defaults)
            upload_config = project.upload if project.upload else None
            privacy = upload_config.privacy if upload_config else "unlisted"
            category_id = upload_config.category_id if upload_config else "10"
            made_for_kids = upload_config.made_for_kids if upload_config else False
            default_language = upload_config.default_language if upload_config else "en"

            log.info(f"Upload settings:")
            log.info(f"  Title: {title}")
            log.info(f"  Privacy: {privacy}")
            log.info(f"  Category ID: {category_id}")
            log.info(f"  Made for kids: {made_for_kids}")
            log.info(f"  Default language: {default_language}")
            log.info(f"  Tags: {', '.join(tags) if tags else 'None'}")

            # Hard gate: require a generated thumbnail before uploading
            if not project.render.thumbnail_path:
                raise RuntimeError(
                    "Render step must generate a thumbnail before upload. "
                    "No thumbnail path found in project.render."
                )
            thumbnail_path = project_dir / project.render.thumbnail_path
            if not thumbnail_path.exists():
                raise FileNotFoundError(
                    f"Thumbnail file not found: {thumbnail_path}. "
                    "Please re-run render to generate it."
                )
            log.info(f"Thumbnail available: {thumbnail_path.resolve()}")

            # Upload video
            log.info("Starting resumable upload...")
            try:
                response = provider.upload_video(
                    video_path=video_path,
                    title=title,
                    description=description,
                    tags=tags,
                    privacy_status=privacy,
                    category_id=category_id,
                    made_for_kids=made_for_kids,
                    default_language=default_language,
                )
            except Exception as e:
                # Log raw error details for debugging
                log.error(f"Upload failed with error: {e}")
                if hasattr(e, "content"):
                    log.error(f"Raw error content: {e.content}")
                raise

            video_id = response["id"]
            log.info(f"Video uploaded successfully! Video ID: {video_id}")

            # Upload thumbnail (required)
            log.info(f"Uploading custom thumbnail: {thumbnail_path.resolve()}")
            provider.upload_thumbnail(video_id, thumbnail_path)
            thumbnail_uploaded = True
            log.info("Thumbnail uploaded successfully")

            # Persist YouTube data to project.json
            project.youtube = YouTubeData(
                video_id=video_id,
                uploaded_at=datetime.now().isoformat(),
                privacy=privacy,
                title=title,
                thumbnail_uploaded=thumbnail_uploaded,
                thumbnail_path=str(project.render.thumbnail_path) if project.render.thumbnail_path else None,
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

