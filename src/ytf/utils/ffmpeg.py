"""
FFmpeg utilities for audio/video processing.

Provides functions for concatenating audio, normalizing loudness, and creating video files.
"""

import subprocess
import tempfile
from pathlib import Path
from typing import Union


def check_ffmpeg() -> bool:
    """
    Check if FFmpeg is available.

    Returns:
        True if FFmpeg is available, False otherwise
    """
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def generate_default_background(output_path: Union[str, Path], width: int = 1920, height: int = 1080) -> None:
    """
    Generate a default solid color background image using FFmpeg.

    Args:
        output_path: Path where to save the background image
        width: Image width in pixels (default 1920)
        height: Image height in pixels (default 1080)

    Raises:
        RuntimeError: If FFmpeg fails to generate the image
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        result = subprocess.run(
            [
                "ffmpeg",
                "-f", "lavfi",
                "-i", f"color=c=black:s={width}x{height}:d=1",
                "-frames:v", "1",
                "-y",  # Overwrite if exists
                str(output_path),
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode != 0:
            raise RuntimeError(
                f"FFmpeg failed to generate background: {result.stderr or result.stdout}"
            )

        if not output_path.exists():
            raise RuntimeError(f"Background image was not created at {output_path}")

    except subprocess.TimeoutExpired:
        raise RuntimeError("FFmpeg timed out while generating background") from None
    except Exception as e:
        raise RuntimeError(f"FFmpeg error generating background: {e}") from e


def concatenate_audio_files(
    audio_files: list[Union[str, Path]], output_path: Union[str, Path]
) -> None:
    """
    Concatenate multiple audio files using FFmpeg concat demuxer.

    Args:
        audio_files: List of paths to audio files to concatenate
        output_path: Path where to save the concatenated audio

    Raises:
        RuntimeError: If FFmpeg fails to concatenate files
        FileNotFoundError: If any input file doesn't exist
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Validate all input files exist
    for audio_file in audio_files:
        audio_path = Path(audio_file)
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

    # Create temporary file list for concat demuxer
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        concat_list_path = Path(f.name)
        for audio_file in audio_files:
            # Use absolute paths and escape single quotes
            abs_path = Path(audio_file).resolve()
            f.write(f"file '{abs_path}'\n")

    try:
        result = subprocess.run(
            [
                "ffmpeg",
                "-f", "concat",
                "-safe", "0",
                "-i", str(concat_list_path),
                "-c", "copy",
                "-y",  # Overwrite if exists
                str(output_path),
            ],
            capture_output=True,
            text=True,
            timeout=600,  # 10 minutes max for concatenation
        )

        if result.returncode != 0:
            raise RuntimeError(
                f"FFmpeg failed to concatenate audio: {result.stderr or result.stdout}"
            )

        if not output_path.exists():
            raise RuntimeError(f"Concatenated audio was not created at {output_path}")

    except subprocess.TimeoutExpired:
        raise RuntimeError("FFmpeg timed out while concatenating audio") from None
    except Exception as e:
        raise RuntimeError(f"FFmpeg error concatenating audio: {e}") from e
    finally:
        # Clean up temp file
        if concat_list_path.exists():
            concat_list_path.unlink()


def normalize_loudness(
    input_path: Union[str, Path], output_path: Union[str, Path], target_lufs: float = -16.0
) -> None:
    """
    Normalize audio loudness using FFmpeg loudnorm filter.

    Args:
        input_path: Path to input audio file
        output_path: Path where to save the normalized audio
        target_lufs: Target integrated loudness in LUFS (default -16.0, YouTube standard)

    Raises:
        RuntimeError: If FFmpeg fails to normalize audio
        FileNotFoundError: If input file doesn't exist
    """
    input_path = Path(input_path)
    output_path = Path(output_path)

    if not input_path.exists():
        raise FileNotFoundError(f"Input audio file not found: {input_path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        result = subprocess.run(
            [
                "ffmpeg",
                "-i", str(input_path),
                "-af", f"loudnorm=I={target_lufs}:TP=-1.5:LRA=11",
                "-y",  # Overwrite if exists
                str(output_path),
            ],
            capture_output=True,
            text=True,
            timeout=600,  # 10 minutes max for normalization
        )

        if result.returncode != 0:
            raise RuntimeError(
                f"FFmpeg failed to normalize loudness: {result.stderr or result.stdout}"
            )

        if not output_path.exists():
            raise RuntimeError(f"Normalized audio was not created at {output_path}")

    except subprocess.TimeoutExpired:
        raise RuntimeError("FFmpeg timed out while normalizing loudness") from None
    except Exception as e:
        raise RuntimeError(f"FFmpeg error normalizing loudness: {e}") from e


def create_video_from_image_and_audio(
    image_path: Union[str, Path],
    audio_path: Union[str, Path],
    output_path: Union[str, Path],
    width: int = 1920,
    height: int = 1080,
    fps: int = 30,
) -> None:
    """
    Create an MP4 video by looping a static image and muxing with audio.

    Args:
        image_path: Path to background image
        audio_path: Path to audio file
        output_path: Path where to save the output MP4
        width: Video width in pixels (default 1920)
        height: Video height in pixels (default 1080)
        fps: Video frame rate (default 30)

    Raises:
        RuntimeError: If FFmpeg fails to create video
        FileNotFoundError: If input files don't exist
    """
    image_path = Path(image_path)
    audio_path = Path(audio_path)
    output_path = Path(output_path)

    if not image_path.exists():
        raise FileNotFoundError(f"Image file not found: {image_path}")
    if not audio_path.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        # Get audio duration to determine loop duration
        # Use ffprobe to get duration
        probe_result = subprocess.run(
            [
                "ffprobe",
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                str(audio_path),
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )

        if probe_result.returncode != 0:
            raise RuntimeError(
                f"Failed to get audio duration: {probe_result.stderr or probe_result.stdout}"
            )

        duration = float(probe_result.stdout.strip())

        # Create video by looping image for the duration of the audio
        result = subprocess.run(
            [
                "ffmpeg",
                "-loop", "1",
                "-i", str(image_path),
                "-i", str(audio_path),
                "-c:v", "libx264",
                "-tune", "stillimage",
                "-c:a", "aac",
                "-b:a", "192k",
                "-pix_fmt", "yuv420p",
                "-shortest",
                "-s", f"{width}x{height}",
                "-r", str(fps),
                "-y",  # Overwrite if exists
                str(output_path),
            ],
            capture_output=True,
            text=True,
            timeout=600,  # 10 minutes max
        )

        if result.returncode != 0:
            raise RuntimeError(
                f"FFmpeg failed to create video: {result.stderr or result.stdout}"
            )

        if not output_path.exists():
            raise RuntimeError(f"Video was not created at {output_path}")

    except subprocess.TimeoutExpired:
        raise RuntimeError("FFmpeg timed out while creating video") from None
    except ValueError as e:
        raise RuntimeError(f"Invalid audio duration: {e}") from e
    except Exception as e:
        raise RuntimeError(f"FFmpeg error creating video: {e}") from e

