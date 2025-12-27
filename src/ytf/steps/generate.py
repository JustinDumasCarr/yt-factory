"""
Generate step: Generate music tracks (skeleton in Sprint 1).

In Sprint 1, this step only loads the project, sets status, and logs.
Actual Suno integration will be implemented in a future sprint.
"""

from ytf.logger import StepLogger
from ytf.project import load_project, save_project, update_status


def run(project_id: str) -> None:
    """
    Run the generate step (skeleton implementation).

    Args:
        project_id: Project ID

    Raises:
        Exception: If step fails (error persisted to project.json)
    """
    project = load_project(project_id)

    with StepLogger(project_id, "generate") as log:
        try:
            update_status(project, "generate")
            save_project(project)

            log.info("Starting generate step (not implemented yet)")
            log.info("This step will generate music tracks using Suno API in a future sprint.")

            # TODO: Actual implementation in future sprint
            # - For each prompt in project.json.plan.prompts:
            #   - Submit generation job to Suno
            #   - Poll until ready
            #   - Download audio file
            #   - Compute duration
            #   - Save to project.json.tracks[]

            # Mark as successful (skeleton)
            update_status(project, "generate", error=None)
            save_project(project)

            log.info("Generate step completed (skeleton)")
        except Exception as e:
            update_status(project, "generate", error=e)
            save_project(project)
            log.error(f"Generate step failed: {e}")
            raise

