"""
Generate step: Generate music tracks using Suno API.

For each planned prompt, submits a generation job, polls until complete,
downloads audio, computes duration, and persists to project.json.tracks[].
Per-track failures do not stop the step - it continues with remaining tracks.
"""

import json
from pathlib import Path

from ytf.logger import StepLogger
from ytf.project import (
    PROJECTS_DIR,
    Track,
    TrackError,
    load_project,
    save_project,
    update_status,
)
from ytf.providers.suno import SunoProvider
from ytf.utils.ffprobe import get_duration_seconds


def run(project_id: str) -> None:
    """
    Run the generate step with full Suno integration.

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

            log.info("Starting generate step with Suno integration")

            # Validate plan exists
            if not project.plan or not project.plan.prompts:
                raise ValueError(
                    "Project plan not found. Run 'ytf plan <id>' first."
                )

            prompts = project.plan.prompts
            log.info(f"Found {len(prompts)} prompts to generate")

            # Initialize Suno provider
            try:
                provider = SunoProvider()
            except ValueError as e:
                log.error(f"Failed to initialize Suno provider: {e}")
                raise

            # Get project directory
            project_dir = PROJECTS_DIR / project_id
            tracks_dir = project_dir / "tracks"
            tracks_dir.mkdir(exist_ok=True)

            # Track existing tracks by index for resume logic
            existing_tracks = {t.track_index: t for t in project.tracks}

            # Get max track attempts (default: 2, can be overridden via project metadata)
            max_track_attempts = 2  # Default, can be passed from queue item in future

            # Process each prompt
            successful = 0
            failed = 0

            for prompt in prompts:
                track_index = prompt.track_index

                try:
                    # Resume logic: skip if track already exists and is OK
                    existing = existing_tracks.get(track_index)
                    if existing and existing.status == "ok" and existing.audio_path:
                        audio_path = project_dir / existing.audio_path
                        if audio_path.exists():
                            log.info(
                                f"Track {track_index} already exists, skipping: {existing.audio_path}"
                            )
                            successful += 1
                            continue

                    # Check attempt cap for failed tracks
                    if existing and existing.status == "failed" and existing.error:
                        attempt_count = existing.error.attempt_count
                        if attempt_count >= max_track_attempts:
                            log.warning(
                                f"Track {track_index} has exceeded max attempts ({attempt_count}/{max_track_attempts}), skipping"
                            )
                            failed += 1
                            continue
                        else:
                            log.info(
                                f"Retrying track {track_index} (attempt {attempt_count + 1}/{max_track_attempts})"
                            )

                    log.info(
                        f"Processing track {track_index}: {prompt.title} ({prompt.style})"
                    )

                    # Resume logic: if we have a job_id but no audio, try polling first
                    # Also check if we have audio_url for resume
                    task_id = None
                    if existing and existing.job_id:
                        task_id = existing.job_id
                        log.info(
                            f"Resuming track {track_index} with existing job_id: {task_id}"
                        )
                    elif existing and existing.audio_url:
                        # If we have audio_url but no file, try downloading directly
                        log.info(
                            f"Resuming track {track_index} with existing audio_url: {existing.audio_url}"
                        )
                        # We'll handle download below, but skip job submission
                        task_id = existing.job_id  # Use existing job_id if available
                    else:
                        # Submit generation job
                        log.info(f"Submitting generation job for track {track_index}")

                        # Prepare prompt text (lyrics if vocals enabled, otherwise None)
                        prompt_text = None
                        if not prompt.vocals_enabled:
                            # Instrumental: no prompt needed
                            prompt_text = None
                        else:
                            # Vocals: use lyrics_text as exact lyrics
                            prompt_text = prompt.lyrics_text

                        task_id = provider.generate_music(
                            style=prompt.style,
                            title=prompt.title,
                            prompt=prompt_text,
                            instrumental=not prompt.vocals_enabled,
                        )

                        log.info(f"Submitted track {track_index}, task_id: {task_id}")

                    # Poll until complete
                    log.info(f"Polling for track {track_index} completion...")
                    status_info = provider.poll_until_complete(task_id)

                    if status_info["status"] == "failed":
                        error_msg = status_info.get("error", "Unknown error")
                        log.error(
                            f"Track {track_index} generation failed: {error_msg}"
                        )
                        log.error(f"Raw response: {status_info.get('raw', 'N/A')}")

                        # Increment attempt count
                        attempt_count = 0
                        if existing and existing.error:
                            attempt_count = existing.error.attempt_count + 1
                        else:
                            attempt_count = 1

                        # Create failed track entry
                        track = Track(
                            track_index=track_index,
                            prompt=prompt.prompt,
                            provider="suno",
                            job_id=task_id,
                            audio_url=existing.audio_url if existing else None,
                            status="failed",
                            error=TrackError(
                                message=error_msg,
                                raw=status_info.get("raw"),
                                attempt_count=attempt_count,
                            ),
                        )

                        # Update or add to tracks list
                        if existing:
                            # Update existing
                            idx = next(
                                (
                                    i
                                    for i, t in enumerate(project.tracks)
                                    if t.track_index == track_index
                                ),
                                None,
                            )
                            if idx is not None:
                                project.tracks[idx] = track
                        else:
                            project.tracks.append(track)

                        save_project(project)
                        failed += 1
                        continue

                    # Get first track from sunoData (musicIndex 0)
                    suno_data = status_info.get("sunoData", [])
                    if not suno_data or len(suno_data) == 0:
                        error_msg = "No tracks returned from Suno"
                        log.error(f"Track {track_index}: {error_msg}")

                        # Increment attempt count
                        attempt_count = 0
                        if existing and existing.error:
                            attempt_count = existing.error.attempt_count + 1
                        else:
                            attempt_count = 1

                        track = Track(
                            track_index=track_index,
                            prompt=prompt.prompt,
                            provider="suno",
                            job_id=task_id,
                            audio_url=existing.audio_url if existing else None,
                            status="failed",
                            error=TrackError(
                                message=error_msg,
                                raw=status_info.get("raw"),
                                attempt_count=attempt_count,
                            ),
                        )

                        if existing:
                            idx = next(
                                (
                                    i
                                    for i, t in enumerate(project.tracks)
                                    if t.track_index == track_index
                                ),
                                None,
                            )
                            if idx is not None:
                                project.tracks[idx] = track
                        else:
                            project.tracks.append(track)

                        save_project(project)
                        failed += 1
                        continue

                    # Use first track (musicIndex 0)
                    track_data = suno_data[0]
                    audio_url = track_data.get("audioUrl")

                    if not audio_url:
                        error_msg = "No audioUrl in track data"
                        log.error(f"Track {track_index}: {error_msg}")

                        # Increment attempt count
                        attempt_count = 0
                        if existing and existing.error:
                            attempt_count = existing.error.attempt_count + 1
                        else:
                            attempt_count = 1

                        track = Track(
                            track_index=track_index,
                            prompt=prompt.prompt,
                            provider="suno",
                            job_id=task_id,
                            audio_url=existing.audio_url if existing else None,
                            status="failed",
                            error=TrackError(
                                message=error_msg,
                                raw=json.dumps(track_data),
                                attempt_count=attempt_count,
                            ),
                        )

                        if existing:
                            idx = next(
                                (
                                    i
                                    for i, t in enumerate(project.tracks)
                                    if t.track_index == track_index
                                ),
                                None,
                            )
                            if idx is not None:
                                project.tracks[idx] = track
                        else:
                            project.tracks.append(track)

                        save_project(project)
                        failed += 1
                        continue

                    # Download audio
                    # Determine file extension from URL or default to mp3
                    audio_ext = "mp3"
                    if "." in audio_url.split("/")[-1]:
                        audio_ext = audio_url.split(".")[-1].split("?")[0]

                    audio_filename = f"track_{track_index:02d}.{audio_ext}"
                    audio_path = tracks_dir / audio_filename
                    relative_audio_path = f"tracks/{audio_filename}"

                    log.info(
                        f"Downloading track {track_index} to {relative_audio_path}"
                    )
                    provider.download_audio(str(audio_url), str(audio_path))

                    # Compute duration
                    log.info(f"Computing duration for track {track_index}")
                    duration = None
                    
                    # Try ffprobe first (canonical method)
                    try:
                        duration = get_duration_seconds(audio_path)
                        log.info(
                            f"Track {track_index} duration (ffprobe): {duration:.2f} seconds"
                        )
                    except Exception as e:
                        log.warning(
                            f"ffprobe failed for track {track_index}: {e}. Trying Suno duration as fallback."
                        )
                        # Fallback: use duration from Suno response if available
                        suno_duration = track_data.get("duration")
                        if suno_duration:
                            try:
                                duration = float(suno_duration)
                                log.info(
                                    f"Track {track_index} duration (from Suno): {duration:.2f} seconds"
                                )
                            except (ValueError, TypeError):
                                log.error(
                                    f"Invalid duration from Suno for track {track_index}: {suno_duration}"
                                )
                                duration = None
                    
                    if duration is None or duration <= 0:
                        error_msg = "Could not determine duration (ffprobe failed and Suno duration unavailable)"
                        log.error(f"Track {track_index}: {error_msg}")
                        # Mark as failed
                        track = Track(
                            track_index=track_index,
                            prompt=prompt.prompt,
                            provider="suno",
                            job_id=task_id,
                            audio_path=str(relative_audio_path),
                            status="failed",
                            error=TrackError(
                                message=error_msg,
                                raw=None,
                            ),
                        )

                        if existing:
                            idx = next(
                                (
                                    i
                                    for i, t in enumerate(project.tracks)
                                    if t.track_index == track_index
                                ),
                                None,
                            )
                            if idx is not None:
                                project.tracks[idx] = track
                        else:
                            project.tracks.append(track)

                        save_project(project)
                        failed += 1
                        continue

                    # Create successful track entry
                    track = Track(
                        track_index=track_index,
                        prompt=prompt.prompt,
                        provider="suno",
                        job_id=task_id,
                        audio_url=audio_url,  # Persist for resume
                        audio_path=str(relative_audio_path),
                        duration_seconds=duration,
                        status="ok",
                    )

                    # Update or add to tracks list
                    if existing:
                        idx = next(
                            (
                                i
                                for i, t in enumerate(project.tracks)
                                if t.track_index == track_index
                            ),
                            None,
                        )
                        if idx is not None:
                            project.tracks[idx] = track
                    else:
                        project.tracks.append(track)

                    save_project(project)
                    successful += 1

                    log.info(
                        f"Track {track_index} completed successfully: {relative_audio_path} ({duration:.2f}s)"
                    )

                    # Log that a second variant exists (but we're not persisting it)
                    if len(suno_data) > 1:
                        log.info(
                            f"Track {track_index}: Note - Suno returned {len(suno_data)} variants, "
                            "only first variant persisted (musicIndex 0)"
                        )

                except Exception as e:
                    # Per-track error - log and continue
                    log.error(f"Track {track_index} failed with exception: {e}")
                    import traceback

                    log.error(f"Track {track_index} traceback:\n{traceback.format_exc()}")

                    # Create failed track entry
                    track = Track(
                        track_index=track_index,
                        prompt=prompt.prompt,
                        provider="suno",
                        status="failed",
                        error=TrackError(
                            message=str(e),
                            raw=traceback.format_exc(),
                        ),
                    )

                    # Update or add
                    existing = existing_tracks.get(track_index)
                    if existing:
                        idx = next(
                            (
                                i
                                for i, t in enumerate(project.tracks)
                                if t.track_index == track_index
                            ),
                            None,
                        )
                        if idx is not None:
                            project.tracks[idx] = track
                    else:
                        project.tracks.append(track)

                    save_project(project)
                    failed += 1
                    continue

            # Mark step as successful
            update_status(project, "generate", error=None)
            save_project(project)

            log.info(
                f"Generate step completed: {successful} successful, {failed} failed"
            )

        except Exception as e:
            update_status(project, "generate", error=e)
            save_project(project)
            log.error(f"Generate step failed: {e}")
            raise

