"""
FFprobe utilities for audio/video analysis.

Uses ffprobe to get duration and other metadata from media files.
"""

import json
import subprocess
from pathlib import Path


def get_duration_seconds(file_path: str | Path) -> float:
    """
    Get duration of audio/video file using ffprobe.

    Args:
        file_path: Path to media file

    Returns:
        Duration in seconds

    Raises:
        FileNotFoundError: If file doesn't exist
        RuntimeError: If ffprobe fails or returns invalid data
    """
    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    try:
        # Use ffprobe to get duration in JSON format
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "json",
                str(file_path),
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode != 0:
            raise RuntimeError(
                f"ffprobe failed: {result.stderr or result.stdout}"
            )

        data = json.loads(result.stdout)
        duration_str = data.get("format", {}).get("duration")

        if not duration_str:
            raise RuntimeError(f"ffprobe returned no duration for {file_path}")

        duration = float(duration_str)

        if duration <= 0:
            raise RuntimeError(
                f"Invalid duration {duration} seconds for {file_path}"
            )

        return duration

    except json.JSONDecodeError as e:
        raise RuntimeError(f"Failed to parse ffprobe output: {e}") from e
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"ffprobe timed out for {file_path}") from None
    except Exception as e:
        raise RuntimeError(f"ffprobe error: {e}") from e

