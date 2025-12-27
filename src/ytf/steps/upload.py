"""
Upload step: Upload to YouTube (skeleton in Sprint 1).

In Sprint 1, this step only loads the project, sets status, and logs.
Actual YouTube Data API integration will be implemented in a future sprint.
"""

from ytf.logger import StepLogger
from ytf.project import load_project, save_project, update_status


def run(project_id: str) -> None:
    """
    Run the upload step (skeleton implementation).

    Args:
        project_id: Project ID

    Raises:
        Exception: If step fails (error persisted to project.json)
    """
    project = load_project(project_id)

    with StepLogger(project_id, "upload") as log:
        try:
            update_status(project, "upload")
            save_project(project)

            log.info("Starting upload step (not implemented yet)")
            log.info("This step will upload video to YouTube using Data API in a future sprint.")

            # TODO: Actual implementation in future sprint
            # - OAuth authentication (cache token)
            # - Resumable upload of final.mp4
            # - Apply metadata (title, description, tags, privacy)
            # - Save video_id to project.json.youtube

            # Mark as successful (skeleton)
            update_status(project, "upload", error=None)
            save_project(project)

            log.info("Upload step completed (skeleton)")
        except Exception as e:
            update_status(project, "upload", error=e)
            save_project(project)
            log.error(f"Upload step failed: {e}")
            raise

