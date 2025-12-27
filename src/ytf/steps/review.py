"""
Review step: Quality control and manual approval gates.

Runs QC checks on all tracks, generates reports, and honors approved.txt/rejected.txt.
Persists QC results to project.json.
"""

import json
from pathlib import Path

from ytf.channel import get_channel
from ytf.logger import StepLogger
from ytf.project import (
    PROJECTS_DIR,
    QCIssue,
    ReviewData,
    TrackQC,
    load_project,
    save_project,
    update_status,
)
from ytf.utils import ffprobe
from ytf.utils.qc import detect_leading_silence


def run(project_id: str) -> None:
    """
    Run the review step with QC checks and approval gates.

    Args:
        project_id: Project ID

    Raises:
        Exception: If step fails (error persisted to project.json)
    """
    project = load_project(project_id)
    project_dir = PROJECTS_DIR / project_id

    with StepLogger(project_id, "review") as log:
        try:
            update_status(project, "review")
            save_project(project)

            log.info("Starting review step with QC checks")

            # Validate channel_id is set
            if not project.channel_id:
                raise ValueError("Project missing channel_id. Run 'ytf new' with --channel first.")

            # Load channel profile for QC thresholds
            try:
                channel = get_channel(project.channel_id)
                log.info(f"Channel: {project.channel_id} ({channel.name})")
            except Exception as e:
                log.error(f"Failed to load channel profile: {e}")
                raise

            # Get QC thresholds from channel
            min_track_seconds = channel.duration_rules.min_track_seconds
            max_leading_silence_seconds = 3.0  # Default, can be made channel-configurable later

            # Filter to tracks with status=="ok" and audio_path exists
            available_tracks = [
                track
                for track in project.tracks
                if track.status == "ok" and track.audio_path is not None
            ]

            log.info(f"Found {len(available_tracks)} tracks to review")

            # Read manual approval/rejection files if they exist
            approved_path = project_dir / "approved.txt"
            rejected_path = project_dir / "rejected.txt"

            approved_indices = set()
            rejected_indices = set()

            if approved_path.exists():
                log.info(f"Reading approved.txt: {approved_path}")
                with open(approved_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#"):
                            try:
                                idx = int(line)
                                approved_indices.add(idx)
                            except ValueError:
                                log.warning(f"Invalid track index in approved.txt: {line}")

            if rejected_path.exists():
                log.info(f"Reading rejected.txt: {rejected_path}")
                with open(rejected_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#"):
                            try:
                                idx = int(line)
                                rejected_indices.add(idx)
                            except ValueError:
                                log.warning(f"Invalid track index in rejected.txt: {line}")

            # Run QC checks on each track
            qc_results = []
            passed_count = 0
            failed_count = 0

            for track in available_tracks:
                track_index = track.track_index
                audio_path = project_dir / track.audio_path

                # Initialize QC result
                qc = TrackQC(passed=True, issues=[], measured={})

                # Check if manually rejected
                if track_index in rejected_indices:
                    qc.passed = False
                    qc.issues.append(
                        QCIssue(
                            code="manually_rejected",
                            message="Track manually rejected via rejected.txt",
                        )
                    )
                    log.info(f"Track {track_index}: Manually rejected")
                    failed_count += 1
                # Check if manually approved (skip QC checks)
                elif track_index in approved_indices:
                    qc.passed = True
                    qc.issues.append(
                        QCIssue(
                            code="manually_approved",
                            message="Track manually approved via approved.txt",
                        )
                    )
                    log.info(f"Track {track_index}: Manually approved")
                    passed_count += 1
                else:
                    # Run QC checks
                    log.info(f"Running QC checks on track {track_index}...")

                    # Check 1: File exists
                    if not audio_path.exists():
                        qc.passed = False
                        qc.issues.append(
                            QCIssue(
                                code="missing_file",
                                message=f"Audio file not found: {track.audio_path}",
                            )
                        )
                        log.warning(f"Track {track_index}: Missing audio file")
                    else:
                        # Check 2: Duration (too short)
                        try:
                            duration = ffprobe.get_duration_seconds(audio_path)
                            qc.measured["duration_seconds"] = duration

                            if duration < min_track_seconds:
                                qc.passed = False
                                qc.issues.append(
                                    QCIssue(
                                        code="too_short",
                                        message=f"Track duration {duration:.2f}s is below minimum {min_track_seconds}s",
                                        value=duration,
                                    )
                                )
                                log.warning(
                                    f"Track {track_index}: Too short ({duration:.2f}s < {min_track_seconds}s)"
                                )
                        except Exception as e:
                            qc.passed = False
                            qc.issues.append(
                                QCIssue(
                                    code="duration_check_failed",
                                    message=f"Failed to get duration: {e}",
                                )
                            )
                            log.warning(f"Track {track_index}: Duration check failed: {e}")

                        # Check 3: Leading silence (only if duration check passed)
                        if qc.passed:
                            try:
                                leading_silence = detect_leading_silence(audio_path)
                                if leading_silence is not None:
                                    qc.measured["leading_silence_seconds"] = leading_silence

                                    if leading_silence > max_leading_silence_seconds:
                                        qc.passed = False
                                        qc.issues.append(
                                            QCIssue(
                                                code="leading_silence",
                                                message=f"Leading silence {leading_silence:.2f}s exceeds maximum {max_leading_silence_seconds}s",
                                                value=leading_silence,
                                            )
                                        )
                                        log.warning(
                                            f"Track {track_index}: Excessive leading silence ({leading_silence:.2f}s)"
                                        )
                            except Exception as e:
                                # Leading silence detection failure is not critical
                                log.warning(f"Track {track_index}: Leading silence detection failed: {e}")

                    if qc.passed:
                        passed_count += 1
                    else:
                        failed_count += 1

                # Update track QC
                track.qc = qc
                qc_results.append(
                    {
                        "track_index": track_index,
                        "passed": qc.passed,
                        "issues": [issue.model_dump() for issue in qc.issues],
                        "measured": qc.measured,
                    }
                )

            # Determine final approved/rejected lists
            final_approved = []
            final_rejected = []

            for track in available_tracks:
                if track.qc:
                    if track.qc.passed:
                        final_approved.append(track.track_index)
                    else:
                        final_rejected.append(track.track_index)

            # Generate QC reports
            output_dir = project_dir / "output"
            output_dir.mkdir(exist_ok=True)

            qc_report_json_path = output_dir / "qc_report.json"
            qc_report_txt_path = output_dir / "qc_report.txt"

            # JSON report
            report_json = {
                "project_id": project_id,
                "channel_id": project.channel_id,
                "total_tracks": len(available_tracks),
                "passed_count": passed_count,
                "failed_count": failed_count,
                "approved_count": len(final_approved),
                "rejected_count": len(final_rejected),
                "qc_thresholds": {
                    "min_track_seconds": min_track_seconds,
                    "max_leading_silence_seconds": max_leading_silence_seconds,
                },
                "tracks": qc_results,
            }

            with open(qc_report_json_path, "w", encoding="utf-8") as f:
                json.dump(report_json, f, indent=2, ensure_ascii=False)
                f.write("\n")

            log.info(f"QC report (JSON) saved to {qc_report_json_path}")

            # Text report
            report_lines = []
            report_lines.append("=" * 80)
            report_lines.append("QC Report")
            report_lines.append("=" * 80)
            report_lines.append(f"Project: {project_id}")
            report_lines.append(f"Channel: {project.channel_id}")
            report_lines.append(f"Total tracks reviewed: {len(available_tracks)}")
            report_lines.append(f"Passed: {passed_count}")
            report_lines.append(f"Failed: {failed_count}")
            report_lines.append(f"Approved: {len(final_approved)}")
            report_lines.append(f"Rejected: {len(final_rejected)}")
            report_lines.append("")
            report_lines.append("QC Thresholds:")
            report_lines.append(f"  Min track duration: {min_track_seconds}s")
            report_lines.append(f"  Max leading silence: {max_leading_silence_seconds}s")
            report_lines.append("")
            report_lines.append("=" * 80)
            report_lines.append("Track Details")
            report_lines.append("=" * 80)

            for result in qc_results:
                track_idx = result["track_index"]
                status = "PASS" if result["passed"] else "FAIL"
                report_lines.append(f"\nTrack {track_idx}: {status}")
                if result["measured"]:
                    for key, value in result["measured"].items():
                        report_lines.append(f"  {key}: {value:.2f}")
                if result["issues"]:
                    for issue in result["issues"]:
                        report_lines.append(f"  Issue: [{issue['code']}] {issue['message']}")

            report_lines.append("")
            report_lines.append("=" * 80)
            report_lines.append("Approved Tracks")
            report_lines.append("=" * 80)
            if final_approved:
                report_lines.append(", ".join(str(idx) for idx in sorted(final_approved)))
            else:
                report_lines.append("(none)")

            report_lines.append("")
            report_lines.append("=" * 80)
            report_lines.append("Rejected Tracks")
            report_lines.append("=" * 80)
            if final_rejected:
                report_lines.append(", ".join(str(idx) for idx in sorted(final_rejected)))
            else:
                report_lines.append("(none)")

            with open(qc_report_txt_path, "w", encoding="utf-8") as f:
                f.write("\n".join(report_lines))
                f.write("\n")

            log.info(f"QC report (text) saved to {qc_report_txt_path}")

            # Persist review data to project.json
            project.review = ReviewData(
                qc_report_json_path=str(qc_report_json_path.relative_to(project_dir)),
                qc_report_txt_path=str(qc_report_txt_path.relative_to(project_dir)),
                approved_track_indices=final_approved,
                rejected_track_indices=final_rejected,
                qc_summary={
                    "total_tracks": len(available_tracks),
                    "passed_count": passed_count,
                    "failed_count": failed_count,
                    "approved_count": len(final_approved),
                    "rejected_count": len(final_rejected),
                },
            )

            # Save updated tracks with QC data
            save_project(project)

            # Mark as successful
            update_status(project, "review", error=None)
            save_project(project)

            log.info("Review step completed successfully")
            log.info(f"Approved tracks: {len(final_approved)}")
            log.info(f"Rejected tracks: {len(final_rejected)}")

        except Exception as e:
            update_status(project, "review", error=e)
            save_project(project)
            log.error(f"Review step failed: {e}")
            raise

