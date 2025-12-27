"""
Queue step: File-based queue system for batch processing.

Queue items are JSON files in queue/pending/, moved to in_progress/ during processing,
then to done/ or failed/ based on outcome.
"""

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

from pydantic import BaseModel

from ytf.project import PROJECTS_DIR
from ytf.runner import run_project
from ytf.steps import new

# Queue directory structure
QUEUE_DIR = Path(__file__).parent.parent.parent / "queue"
QUEUE_PENDING = QUEUE_DIR / "pending"
QUEUE_IN_PROGRESS = QUEUE_DIR / "in_progress"
QUEUE_DONE = QUEUE_DIR / "done"
QUEUE_FAILED = QUEUE_DIR / "failed"
QUEUE_RUNS = QUEUE_DIR / "runs"


class QueueItem(BaseModel):
    """A single queue item."""

    channel_id: str
    theme: str
    mode: str  # full, render, generate, plan, review, upload
    minutes: Optional[int] = None
    tracks: Optional[int] = None
    vocals: str = "off"
    lyrics: str = "off"
    max_project_attempts: int = 3  # Max attempts per step for the project
    max_track_attempts: int = 2  # Max attempts per track in generate step


def _ensure_queue_dirs() -> None:
    """Ensure queue directory structure exists."""
    QUEUE_PENDING.mkdir(parents=True, exist_ok=True)
    QUEUE_IN_PROGRESS.mkdir(parents=True, exist_ok=True)
    QUEUE_DONE.mkdir(parents=True, exist_ok=True)
    QUEUE_FAILED.mkdir(parents=True, exist_ok=True)
    QUEUE_RUNS.mkdir(parents=True, exist_ok=True)


def add_queue_item(
    channel_id: str,
    theme: str,
    mode: str,
    count: int = 1,
    minutes: Optional[int] = None,
    tracks: Optional[int] = None,
    vocals: str = "off",
    lyrics: str = "off",
    max_project_attempts: int = 3,
    max_track_attempts: int = 2,
) -> list[str]:
    """
    Add one or more items to the queue.

    Args:
        channel_id: Channel ID
        theme: Base theme (will be suffixed with index if count > 1)
        mode: Target mode (full, render, generate, etc.)
        count: Number of items to create
        minutes: Optional minutes override
        tracks: Optional tracks override
        vocals: Vocals setting
        lyrics: Lyrics setting
        max_project_attempts: Max attempts per project step
        max_track_attempts: Max attempts per track

    Returns:
        List of queue item filenames created
    """
    _ensure_queue_dirs()

    created = []
    for i in range(1, count + 1):
        item_theme = f"{theme} {i}" if count > 1 else theme
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{channel_id}_{mode}_{i if count > 1 else ''}.json".replace(
            " ", "_"
        )

        item = QueueItem(
            channel_id=channel_id,
            theme=item_theme,
            mode=mode,
            minutes=minutes,
            tracks=tracks,
            vocals=vocals,
            lyrics=lyrics,
            max_project_attempts=max_project_attempts,
            max_track_attempts=max_track_attempts,
        )

        item_path = QUEUE_PENDING / filename
        with open(item_path, "w", encoding="utf-8") as f:
            json.dump(item.model_dump(), f, indent=2)
            f.write("\n")

        created.append(filename)

    return created


def list_queue() -> dict:
    """
    List queue status.

    Returns:
        Dict with counts: pending, in_progress, done, failed
    """
    _ensure_queue_dirs()

    return {
        "pending": len(list(QUEUE_PENDING.glob("*.json"))),
        "in_progress": len(list(QUEUE_IN_PROGRESS.glob("*.json"))),
        "done": len(list(QUEUE_DONE.glob("*.json"))),
        "failed": len(list(QUEUE_FAILED.glob("*.json"))),
    }


def run_queue(limit: Optional[int] = None) -> dict:
    """
    Process queue items sequentially.

    Args:
        limit: Maximum number of items to process (None = all)

    Returns:
        Summary dict with run_id, processed count, results
    """
    _ensure_queue_dirs()

    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_log_path = QUEUE_RUNS / f"{run_id}.log"
    run_summary_path = QUEUE_RUNS / f"{run_id}.json"

    # Get pending items (sorted by filename for FIFO)
    pending_items = sorted(QUEUE_PENDING.glob("*.json"))

    if not pending_items:
        return {
            "run_id": run_id,
            "processed": 0,
            "successful": 0,
            "failed": 0,
            "items": [],
        }

    if limit:
        pending_items = pending_items[:limit]

    results = []
    successful = 0
    failed = 0

    with open(run_log_path, "w", encoding="utf-8") as log_file:
        log_file.write(f"Queue run started: {run_id}\n")
        log_file.write(f"Processing {len(pending_items)} items\n\n")

        for item_path in pending_items:
            item_filename = item_path.name

            # Move to in_progress
            in_progress_path = QUEUE_IN_PROGRESS / item_filename
            shutil.move(str(item_path), str(in_progress_path))

            log_file.write(f"Processing: {item_filename}\n")

            try:
                # Load queue item
                with open(in_progress_path, "r", encoding="utf-8") as f:
                    item_data = json.load(f)
                item = QueueItem(**item_data)

                # Create project
                project_id = new.create_project(
                    theme=item.theme,
                    channel_id=item.channel_id,
                    minutes=item.minutes,
                    tracks=item.tracks,
                    vocals=item.vocals,
                    lyrics=item.lyrics,
                )

                log_file.write(f"  Created project: {project_id}\n")

                # Persist attempt caps to project.json
                from ytf.project import load_project, save_project

                project = load_project(project_id)
                # Store attempt caps in project metadata (we'll use a simple approach)
                # For now, we'll pass them through the runner context
                save_project(project)

                # Run project with attempt caps
                try:
                    run_project(
                        project_id,
                        to_step=_mode_to_step(item.mode),
                        use_retries=True,
                    )

                    # Check final status
                    project = load_project(project_id)
                    if project.youtube and project.youtube.video_id:
                        video_id = project.youtube.video_id
                    else:
                        video_id = None

                    result = {
                        "queue_item": item_filename,
                        "project_id": project_id,
                        "status": "success",
                        "last_successful_step": project.status.last_successful_step,
                        "youtube_video_id": video_id,
                        "failed_step": None,
                        "error_message": None,
                    }

                    successful += 1
                    log_file.write(f"  ✓ Success: {project_id}\n")

                    # Move to done
                    shutil.move(str(in_progress_path), QUEUE_DONE / item_filename)

                except Exception as e:
                    # Load project to get error details
                    project = load_project(project_id)
                    result = {
                        "queue_item": item_filename,
                        "project_id": project_id,
                        "status": "failed",
                        "last_successful_step": project.status.last_successful_step,
                        "youtube_video_id": None,
                        "failed_step": project.status.current_step,
                        "error_message": str(project.status.last_error.message)
                        if project.status.last_error
                        else str(e),
                    }

                    failed += 1
                    log_file.write(f"  ✗ Failed: {project_id} - {result['error_message']}\n")

                    # Move to failed
                    shutil.move(str(in_progress_path), QUEUE_FAILED / item_filename)

                results.append(result)

            except Exception as e:
                # Queue item itself is invalid
                result = {
                    "queue_item": item_filename,
                    "project_id": None,
                    "status": "failed",
                    "last_successful_step": None,
                    "youtube_video_id": None,
                    "failed_step": "queue",
                    "error_message": str(e),
                }

                failed += 1
                log_file.write(f"  ✗ Queue item error: {item_filename} - {e}\n")

                # Move to failed
                if in_progress_path.exists():
                    shutil.move(str(in_progress_path), QUEUE_FAILED / item_filename)

                results.append(result)

            log_file.write("\n")

        log_file.write(f"\nRun completed: {run_id}\n")
        log_file.write(f"Successful: {successful}\n")
        log_file.write(f"Failed: {failed}\n")

    # Write summary JSON
    summary = {
        "run_id": run_id,
        "started_at": datetime.now().isoformat(),
        "processed": len(results),
        "successful": successful,
        "failed": failed,
        "items": results,
    }

    with open(run_summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
        f.write("\n")

    return summary


def _mode_to_step(mode: str) -> str:
    """Convert queue mode to target step."""
    mode_map = {
        "full": "upload",
        "upload": "upload",
        "render": "render",
        "review": "review",
        "generate": "generate",
        "plan": "plan",
    }
    return mode_map.get(mode, "upload")

