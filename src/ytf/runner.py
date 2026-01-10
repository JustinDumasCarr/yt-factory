"""
Runner: Execute pipeline steps sequentially for a project.

Provides `run_project` to run steps up to a target, and `run_batch` for batch processing.
"""

from datetime import datetime

from ytf.logger import StepLogger
from ytf.project import PROJECTS_DIR, load_project
from ytf.steps import generate, plan, render, review, upload
from ytf.utils.retry import retry_step

# Step execution order
STEP_ORDER = ["plan", "generate", "review", "render", "upload"]


def run_project(
    project_id: str,
    to_step: str = "upload",
    from_step: str | None = None,
    use_retries: bool = False,
) -> None:
    """
    Run pipeline steps sequentially for a project.

    Args:
        project_id: Project ID
        to_step: Target step to run up to (default: "upload")
        from_step: Starting step (default: infer from project.status.last_successful_step)

    Raises:
        ValueError: If step names are invalid
        Exception: If any step fails (error persisted by step module)
    """
    if to_step not in STEP_ORDER:
        raise ValueError(f"Invalid 'to_step': {to_step}. Must be one of {STEP_ORDER}")

    project = load_project(project_id)

    # Find target step index first
    to_idx = STEP_ORDER.index(to_step)

    # Determine starting point
    if from_step:
        if from_step not in STEP_ORDER:
            raise ValueError(f"Invalid 'from_step': {from_step}. Must be one of {STEP_ORDER}")
        start_idx = STEP_ORDER.index(from_step)
    else:
        # Infer from last_successful_step
        last_step = project.status.last_successful_step
        if last_step and last_step in STEP_ORDER:
            # Start from the step after the last successful one
            last_idx = STEP_ORDER.index(last_step)
            start_idx = last_idx + 1
            # Don't go past the target
            if start_idx > to_idx:
                # Already at or past target step
                return
        else:
            # Start from beginning
            start_idx = 0

    # Determine which steps to run
    steps_to_run = STEP_ORDER[start_idx : to_idx + 1]

    if not steps_to_run:
        # Already at or past target step
        return

    # Step function mapping
    step_functions = {
        "plan": plan.run,
        "generate": generate.run,
        "review": review.run,
        "render": render.run,
        "upload": _run_upload_with_skip,
    }

    # Steps that benefit from retries in batch mode
    retriable_steps = {"plan", "generate", "upload"}

    # Run each step
    for step_name in steps_to_run:
        step_func = step_functions[step_name]

        # Apply retry wrapper if enabled and step is retriable
        if use_retries and step_name in retriable_steps:
            retried_func = retry_step(max_retries=3, initial_delay=1.0)(step_func)
            retried_func(project_id)
        else:
            step_func(project_id)


def _run_upload_with_skip(project_id: str) -> None:
    """
    Run upload step, skipping if already uploaded.

    Args:
        project_id: Project ID

    Raises:
        Exception: If upload fails (error persisted by step module)
    """
    project = load_project(project_id)

    # Check if already uploaded
    if project.youtube and project.youtube.video_id:
        # Already uploaded, skip
        with StepLogger(project_id, "upload") as log:
            log.info(
                f"Video already uploaded. Video ID: {project.youtube.video_id}. "
                f"URL: https://www.youtube.com/watch?v={project.youtube.video_id}. "
                "Skipping upload step."
            )
        return

    # Run upload normally
    upload.run(project_id)


def run_batch(
    channel_id: str,
    count: int,
    mode: str,
    base_theme: str,
    batch_id: str | None = None,
) -> dict:
    """
    Create and run multiple projects in batch.

    Args:
        channel_id: Channel ID
        count: Number of projects to create
        mode: Target step mode ("full", "render", "generate", etc.)
        base_theme: Base theme string (will be suffixed with index)
        batch_id: Optional batch ID (default: auto-generated timestamp)

    Returns:
        Dictionary with batch summary:
        - batch_id
        - channel_id
        - mode
        - created_at
        - completed_at
        - projects: list of project outcomes

    Raises:
        ValueError: If mode is invalid
    """
    from ytf.steps import new

    # Map mode to target step
    mode_to_step = {
        "full": "upload",
        "upload": "upload",
        "render": "render",
        "review": "review",
        "generate": "generate",
        "plan": "plan",
    }

    if mode not in mode_to_step:
        raise ValueError(f"Invalid mode: {mode}. Must be one of {list(mode_to_step.keys())}")

    target_step = mode_to_step[mode]

    # Generate batch ID if not provided
    if not batch_id:
        batch_id = datetime.now().strftime("%Y%m%d_%H%M%S_batch")

    created_at = datetime.now().isoformat()

    # Create projects and run them
    projects = []
    for i in range(1, count + 1):
        theme = f"{base_theme} {i}" if count > 1 else base_theme

        project_outcome = {
            "project_id": None,
            "channel_id": channel_id,
            "theme": theme,
            "started_at": None,
            "completed_at": None,
            "last_successful_step": None,
            "failed_step": None,
            "error_message": None,
            "youtube_video_id": None,
        }

        try:
            project_outcome["started_at"] = datetime.now().isoformat()

            # Create project
            project_id = new.create_project(
                theme=theme,
                channel_id=channel_id,
                minutes=None,  # Use channel default
                tracks=None,  # Use channel default
                vocals="off",
                lyrics="off",
            )
            project_outcome["project_id"] = project_id

            # Run pipeline with retries enabled for batch mode
            run_project(project_id, to_step=target_step, use_retries=True)

            # Load final state
            project = load_project(project_id)
            project_outcome["last_successful_step"] = project.status.last_successful_step
            if project.youtube and project.youtube.video_id:
                project_outcome["youtube_video_id"] = project.youtube.video_id

            project_outcome["completed_at"] = datetime.now().isoformat()

        except Exception as e:
            # Capture failure
            project_outcome["completed_at"] = datetime.now().isoformat()

            # Try to load project state for accurate failure info
            if project_outcome["project_id"]:
                try:
                    project = load_project(project_outcome["project_id"])
                    project_outcome["last_successful_step"] = project.status.last_successful_step
                    project_outcome["failed_step"] = project.status.current_step
                    if project.status.last_error:
                        project_outcome["error_message"] = project.status.last_error.message
                except Exception:
                    # If we can't load project, use exception message
                    project_outcome["failed_step"] = "unknown"
                    project_outcome["error_message"] = str(e)
            else:
                # Project creation failed
                project_outcome["failed_step"] = "new"
                project_outcome["error_message"] = str(e)

        projects.append(project_outcome)

    completed_at = datetime.now().isoformat()

    # Build summary
    summary = {
        "batch_id": batch_id,
        "channel_id": channel_id,
        "mode": mode,
        "target_step": target_step,
        "created_at": created_at,
        "completed_at": completed_at,
        "total_projects": count,
        "successful": len([p for p in projects if p["failed_step"] is None]),
        "failed": len([p for p in projects if p["failed_step"] is not None]),
        "projects": projects,
    }

    # Save batch summary to projects directory
    batch_summary_path = PROJECTS_DIR / f"{batch_id}_summary.json"
    import json

    with open(batch_summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
        f.write("\n")

    return summary
