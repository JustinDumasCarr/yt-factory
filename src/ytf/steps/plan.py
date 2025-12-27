"""
Plan step: Generate planning data (skeleton in Sprint 1).

In Sprint 1, this step only loads the project, sets status, and logs.
Actual Gemini integration will be implemented in a future sprint.
"""

from ytf.logger import StepLogger
from ytf.project import load_project, save_project, update_status


def run(project_id: str) -> None:
    """
    Run the plan step (skeleton implementation).

    Args:
        project_id: Project ID

    Raises:
        Exception: If step fails (error persisted to project.json)
    """
    project = load_project(project_id)

    with StepLogger(project_id, "plan") as log:
        try:
            update_status(project, "plan")
            save_project(project)

            log.info("Starting plan step (not implemented yet)")
            log.info("This step will generate prompts and YouTube metadata using Gemini in a future sprint.")

            # TODO: Actual implementation in future sprint
            # - Call Gemini API to generate prompts
            # - Generate optional lyrics if vocals enabled
            # - Generate YouTube metadata (title, description, tags)
            # - Save to project.json.plan

            # Mark as successful (skeleton)
            update_status(project, "plan", error=None)
            save_project(project)

            log.info("Plan step completed (skeleton)")
        except Exception as e:
            update_status(project, "plan", error=e)
            save_project(project)
            log.error(f"Plan step failed: {e}")
            raise

