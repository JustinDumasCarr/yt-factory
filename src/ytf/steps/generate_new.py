"""
Generate step: Generate music tracks using Suno API.

For each planned job, submits a generation job, polls until complete,
downloads both variants, computes duration, and persists to project.json.tracks[].
Per-variant failures do not stop the step - it continues with remaining variants.
"""

import json
import math
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
    Each job produces 2 variants, both are persisted.

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
            log.info(f"Found {len(prompts)} job prompts to generate")

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

            # Track existing tracks by job_index+variant_index for resume logic
            existing_tracks_by_job = {}  # job_index -> {0: Track, 1: Track}
            existing_tracks_by_track_index = {}  # track_index -> Track
            for t in project.tracks:
                existing_tracks_by_track_index[t.track_index] = t
                if hasattr(t, 'job_index') and hasattr(t, 'variant_index'):
                    if t.job_index not in existing_tracks_by_job:
                        existing_tracks_by_job[t.job_index] = {}
                    existing_tracks_by_job[t.job_index][t.variant_index] = t

            # Get max track attempts (default: 2, can be overridden via project metadata)
            max_track_attempts = 2  # Default, can be passed from queue item in future

            # Process each job (each job produces 2 variants)
            successful = 0
            failed = 0
            next_track_index = 0  # Sequential track index across all variants

            for prompt in prompts:
                job_index = prompt.job_index
                
                # Determine track indices for this job's variants
                variant_0_track_index = next_track_index
                variant_1_track_index = next_track_index + 1
                next_track_index += 2

                # Check if both variants already exist
                existing_variants = existing_tracks_by_job.get(job_index, {})
                variant_0_exists = (
                    existing_variants.get(0) and 
                    existing_variants[0].status == "ok" and 
                    existing_variants[0].audio_path and
                    (project_dir / existing_variants[0].audio_path).exists()
                )
                variant_1_exists = (
                    existing_variants.get(1) and 
                    existing_variants[1].status == "ok" and 
                    existing_variants[1].audio_path and
                    (project_dir / existing_variants[1].audio_path).exists()
                )

                if variant_0_exists and variant_1_exists:
                    log.info(
                        f"Job {job_index} already complete (both variants exist), skipping"
                    )
                    successful += 2
                    continue

                # Get or submit job
                task_id = None
                job_tracks = existing_tracks_by_job.get(job_index, {})
                
                # Check if we have a job_id from any existing variant
                for variant_track in job_tracks.values():
                    if variant_track and variant_track.job_id:
                        task_id = variant_track.job_id
                        log.info(f"Resuming job {job_index} with existing job_id: {task_id}")
                        break

                if not task_id:
                    # Submit generation job
                    log.info(f"Submitting generation job {job_index}: {prompt.title} ({prompt.style})")

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

                    log.info(f"Submitted job {job_index}, task_id: {task_id}")

                # Poll until complete
                log.info(f"Polling for job {job_index} completion...")
                status_info = provider.poll_until_complete(task_id)

                if status_info["status"] == "failed":
                    error_msg = status_info.get("error", "Unknown error")
                    log.error(f"Job {job_index} generation failed: {error_msg}")
                    log.error(f"Raw response: {status_info.get('raw', 'N/A')}")

                    # Mark both variants as failed
                    for variant_idx in [0, 1]:
                        track_index = variant_0_track_index if variant_idx == 0 else variant_1_track_index
                        variant_title = f"{prompt.title} {'I' if variant_idx == 0 else 'II'}"
                        
                        existing = existing_tracks_by_track_index.get(track_index)
                        attempt_count = 0
                        if existing and existing.error:
                            attempt_count = existing.error.attempt_count + 1
                        else:
                            attempt_count = 1

                        track = Track(
                            track_index=track_index,
                            title=variant_title,
                            style=prompt.style,
                            prompt=prompt.prompt,
                            provider="suno",
                            job_id=task_id,
                            job_index=job_index,
                            variant_index=variant_idx,
                            status="failed",
                            error=TrackError(
                                message=error_msg,
                                raw=status_info.get("raw"),
                                attempt_count=attempt_count,
                            ),
                        )

                        # Update or add
                        if existing:
                            idx = next(
                                (i for i, t in enumerate(project.tracks) if t.track_index == track_index),
                                None,
                            )
                            if idx is not None:
                                project.tracks[idx] = track
                        else:
                            project.tracks.append(track)

                    save_project(project)
                    failed += 2
                    continue

                # Get sunoData with both variants
                suno_data = status_info.get("sunoData", [])
                if not suno_data or len(suno_data) == 0:
                    error_msg = "No tracks returned from Suno"
                    log.error(f"Job {job_index}: {error_msg}")

                    # Mark both variants as failed
                    for variant_idx in [0, 1]:
                        track_index = variant_0_track_index if variant_idx == 0 else variant_1_track_index
                        variant_title = f"{prompt.title} {'I' if variant_idx == 0 else 'II'}"
                        
                        existing = existing_tracks_by_track_index.get(track_index)
                        attempt_count = 0
                        if existing and existing.error:
                            attempt_count = existing.error.attempt_count + 1
                        else:
                            attempt_count = 1

                        track = Track(
                            track_index=track_index,
                            title=variant_title,
                            style=prompt.style,
                            prompt=prompt.prompt,
                            provider="suno",
                            job_id=task_id,
                            job_index=job_index,
                            variant_index=variant_idx,
                            status="failed",
                            error=TrackError(
                                message=error_msg,
                                raw=status_info.get("raw"),
                                attempt_count=attempt_count,
                            ),
                        )

                        if existing:
                            idx = next(
                                (i for i, t in enumerate(project.tracks) if t.track_index == track_index),
                                None,
                            )
                            if idx is not None:
                                project.tracks[idx] = track
                        else:
                            project.tracks.append(track)

                    save_project(project)
                    failed += 2
                    continue

                # Process both variants
                for variant_idx in [0, 1]:
                    track_index = variant_0_track_index if variant_idx == 0 else variant_1_track_index
                    variant_title = f"{prompt.title} {'I' if variant_idx == 0 else 'II'}"
                    
                    # Check if this variant already exists
                    existing = existing_tracks_by_track_index.get(track_index)
                    if existing and existing.status == "ok" and existing.audio_path:
                        audio_path = project_dir / existing.audio_path
                        if audio_path.exists():
                            log.info(
                                f"Variant {variant_idx} (track {track_index}) already exists, skipping: {existing.audio_path}"
                            )
                            successful += 1
                            continue

                    # Find variant data in suno_data
                    if variant_idx >= len(suno_data):
                        error_msg = f"Variant {variant_idx} not available in Suno response (only {len(suno_data)} variants)"
                        log.error(f"Track {track_index}: {error_msg}")
                        
                        attempt_count = 0
                        if existing and existing.error:
                            attempt_count = existing.error.attempt_count + 1
                        else:
                            attempt_count = 1

                        track = Track(
                            track_index=track_index,
                            title=variant_title,
                            style=prompt.style,
                            prompt=prompt.prompt,
                            provider="suno",
                            job_id=task_id,
                            job_index=job_index,
                            variant_index=variant_idx,
                            status="failed",
                            error=TrackError(
                                message=error_msg,
                                raw=status_info.get("raw"),
                                attempt_count=attempt_count,
                            ),
                        )

                        if existing:
                            idx = next(
                                (i for i, t in enumerate(project.tracks) if t.track_index == track_index),
                                None,
                            )
                            if idx is not None:
                                project.tracks[idx] = track
                        else:
                            project.tracks.append(track)

                        save_project(project)
                        failed += 1
                        continue

                    variant_data = suno_data[variant_idx]
                    if not isinstance(variant_data, dict):
                        error_msg = f"Variant {variant_idx} data is not a dict"
                        log.error(f"Track {track_index}: {error_msg}")
                        
                        attempt_count = 0
                        if existing and existing.error:
                            attempt_count = existing.error.attempt_count + 1
                        else:
                            attempt_count = 1

                        track = Track(
                            track_index=track_index,
                            title=variant_title,
                            style=prompt.style,
                            prompt=prompt.prompt,
                            provider="suno",
                            job_id=task_id,
                            job_index=job_index,
                            variant_index=variant_idx,
                            status="failed",
                            error=TrackError(
                                message=error_msg,
                                raw=json.dumps(variant_data),
                                attempt_count=attempt_count,
                            ),
                        )

                        if existing:
                            idx = next(
                                (i for i, t in enumerate(project.tracks) if t.track_index == track_index),
                                None,
                            )
                            if idx is not None:
                                project.tracks[idx] = track
                        else:
                            project.tracks.append(track)

                        save_project(project)
                        failed += 1
                        continue

                    # Get audio URL (prefer audioUrl, fallback to streamAudioUrl)
                    audio_url = (variant_data.get("audioUrl") or "").strip()
                    if not audio_url:
                        audio_url = (variant_data.get("streamAudioUrl") or "").strip()

                    if not audio_url:
                        error_msg = "No usable audio URL (audioUrl/streamAudioUrl) in variant data"
                        log.error(f"Track {track_index}: {error_msg}")
                        
                        attempt_count = 0
                        if existing and existing.error:
                            attempt_count = existing.error.attempt_count + 1
                        else:
                            attempt_count = 1

                        track = Track(
                            track_index=track_index,
                            title=variant_title,
                            style=prompt.style,
                            prompt=prompt.prompt,
                            provider="suno",
                            job_id=task_id,
                            job_index=job_index,
                            variant_index=variant_idx,
                            status="failed",
                            error=TrackError(
                                message=error_msg,
                                raw=json.dumps(variant_data),
                                attempt_count=attempt_count,
                            ),
                        )

                        if existing:
                            idx = next(
                                (i for i, t in enumerate(project.tracks) if t.track_index == track_index),
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
                    audio_ext = "mp3"
                    if "." in audio_url.split("/")[-1]:
                        audio_ext = audio_url.split(".")[-1].split("?")[0]

                    audio_filename = f"track_{track_index:02d}.{audio_ext}"
                    audio_path = tracks_dir / audio_filename
                    relative_audio_path = f"tracks/{audio_filename}"

                    log.info(f"Downloading variant {variant_idx} (track {track_index}) to {relative_audio_path}")
                    try:
                        provider.download_audio(str(audio_url), str(audio_path))
                    except Exception as e:
                        error_msg = f"Failed to download audio: {e}"
                        log.error(f"Track {track_index}: {error_msg}")
                        
                        attempt_count = 0
                        if existing and existing.error:
                            attempt_count = existing.error.attempt_count + 1
                        else:
                            attempt_count = 1

                        track = Track(
                            track_index=track_index,
                            title=variant_title,
                            style=prompt.style,
                            prompt=prompt.prompt,
                            provider="suno",
                            job_id=task_id,
                            job_index=job_index,
                            variant_index=variant_idx,
                            status="failed",
                            error=TrackError(
                                message=error_msg,
                                raw=str(e),
                                attempt_count=attempt_count,
                            ),
                        )

                        if existing:
                            idx = next(
                                (i for i, t in enumerate(project.tracks) if t.track_index == track_index),
                                None,
                            )
                            if idx is not None:
                                project.tracks[idx] = track
                        else:
                            project.tracks.append(track)

                        save_project(project)
                        failed += 1
                        continue

                    # Compute duration
                    log.info(f"Computing duration for track {track_index}")
                    duration = None
                    
                    try:
                        duration = get_duration_seconds(audio_path)
                        log.info(f"Track {track_index} duration (ffprobe): {duration:.2f} seconds")
                    except Exception as e:
                        log.warning(f"ffprobe failed for track {track_index}: {e}. Trying Suno duration as fallback.")
                        suno_duration = variant_data.get("duration")
                        if suno_duration:
                            try:
                                duration = float(suno_duration)
                                log.info(f"Track {track_index} duration (from Suno): {duration:.2f} seconds")
                            except (ValueError, TypeError):
                                log.error(f"Invalid duration from Suno for track {track_index}: {suno_duration}")
                                duration = None
                    
                    if duration is None or duration <= 0:
                        error_msg = "Could not determine duration (ffprobe failed and Suno duration unavailable)"
                        log.error(f"Track {track_index}: {error_msg}")
                        
                        track = Track(
                            track_index=track_index,
                            title=variant_title,
                            style=prompt.style,
                            prompt=prompt.prompt,
                            provider="suno",
                            job_id=task_id,
                            job_index=job_index,
                            variant_index=variant_idx,
                            audio_path=str(relative_audio_path),
                            status="failed",
                            error=TrackError(
                                message=error_msg,
                                raw=None,
                            ),
                        )

                        if existing:
                            idx = next(
                                (i for i, t in enumerate(project.tracks) if t.track_index == track_index),
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
                        title=variant_title,
                        style=prompt.style,
                        prompt=prompt.prompt,
                        provider="suno",
                        job_id=task_id,
                        job_index=job_index,
                        variant_index=variant_idx,
                        audio_url=audio_url,  # Persist for resume
                        audio_path=str(relative_audio_path),
                        duration_seconds=duration,
                        status="ok",
                    )

                    # Update or add to tracks list
                    if existing:
                        idx = next(
                            (i for i, t in enumerate(project.tracks) if t.track_index == track_index),
                            None,
                        )
                        if idx is not None:
                            project.tracks[idx] = track
                    else:
                        project.tracks.append(track)

                    save_project(project)
                    successful += 1

                    log.info(
                        f"Variant {variant_idx} (track {track_index}) completed successfully: "
                        f"{relative_audio_path} ({duration:.2f}s)"
                    )

            log.info(f"Generate step completed: {successful} successful, {failed} failed")
            update_status(project, "generate", error=None)
            save_project(project)

        except Exception as e:
            update_status(project, "generate", error=e)
            save_project(project)
            log.error(f"Generate step failed: {e}")
            raise

