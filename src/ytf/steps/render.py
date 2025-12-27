"""
Render step: Render final video (skeleton in Sprint 1).

In Sprint 1, this step only loads the project, sets status, and logs.
Actual FFmpeg rendering will be implemented in a future sprint.
"""

from ytf.logger import StepLogger
from ytf.project import load_project, save_project, update_status


def run(project_id: str) -> None:
    """
    Run the render step (skeleton implementation).

    Args:
        project_id: Project ID

    Raises:
        Exception: If step fails (error persisted to project.json)
    """
    project = load_project(project_id)

    with StepLogger(project_id, "render") as log:
        try:
            update_status(project, "render")
            save_project(project)

            log.info("Starting render step (not implemented yet)")
            log.info("This step will render final MP4 using FFmpeg in a future sprint.")

            # TODO: Actual implementation in future sprint
            # - Select tracks to reach target_minutes
            # - Concatenate audio tracks
            # - Normalize loudness
            # - Mux static image + audio into MP4
            # - Generate chapters.txt
            # - Generate youtube_description.txt
            # - Save to project.json.render

            # Mark as successful (skeleton)
            update_status(project, "render", error=None)
            save_project(project)

            log.info("Render step completed (skeleton)")
        except Exception as e:
            update_status(project, "render", error=e)
            save_project(project)
            log.error(f"Render step failed: {e}")
            raise

