"""
QC utilities for track quality control.

Provides functions for detecting leading silence and other audio quality issues.
"""

import re
import subprocess
from pathlib import Path


def detect_leading_silence(
    audio_path: str | Path, silence_threshold: float = -50.0, duration: float = 5.0
) -> float | None:
    """
    Detect leading silence in an audio file using FFmpeg silencedetect.

    Args:
        audio_path: Path to audio file
        silence_threshold: Silence threshold in dB (default -50.0)
        duration: Maximum duration to analyze in seconds (default 5.0)

    Returns:
        Leading silence duration in seconds, or None if no leading silence detected

    Raises:
        FileNotFoundError: If audio file doesn't exist
        RuntimeError: If FFmpeg fails
    """
    audio_path = Path(audio_path)

    if not audio_path.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    try:
        # Run silencedetect on first N seconds
        result = subprocess.run(
            [
                "ffmpeg",
                "-i",
                str(audio_path),
                "-af",
                f"silencedetect=noise={silence_threshold}dB:d=0.3",
                "-t",
                str(duration),  # Analyze only first N seconds
                "-f",
                "null",
                "-",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        # Parse stderr for silence_start and silence_end
        stderr = result.stderr

        # Look for silence_start pattern: "silence_start: 0.123456"
        silence_start_match = re.search(r"silence_start:\s*([\d.]+)", stderr)
        silence_end_match = re.search(r"silence_end:\s*([\d.]+)", stderr)

        if silence_start_match:
            start_time = float(silence_start_match.group(1))
            # If silence starts at 0 or very close to 0, we have leading silence
            if start_time < 0.5:  # Allow 0.5s tolerance
                if silence_end_match:
                    end_time = float(silence_end_match.group(1))
                    return end_time - start_time
                else:
                    # Silence continues to the end of analyzed duration
                    return duration - start_time

        return None

    except subprocess.TimeoutExpired:
        raise RuntimeError(f"FFmpeg timed out while detecting silence in {audio_path}") from None
    except Exception as e:
        raise RuntimeError(f"FFmpeg error detecting silence: {e}") from e
