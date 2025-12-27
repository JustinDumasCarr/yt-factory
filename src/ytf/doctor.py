"""
Doctor command: validate prerequisites before running the pipeline.

Checks:
- FFmpeg and FFprobe installed
- Required environment variables present
- Projects directory is writable
"""

import os
import subprocess
import sys
from pathlib import Path

from ytf.project import PROJECTS_DIR


def check_ffmpeg() -> tuple[bool, str]:
    """
    Check if FFmpeg is installed and accessible.

    Returns:
        (success, message) tuple
    """
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return True, "FFmpeg is installed"
        return False, "FFmpeg command failed"
    except FileNotFoundError:
        return False, "FFmpeg not found in PATH"
    except subprocess.TimeoutExpired:
        return False, "FFmpeg check timed out"
    except Exception as e:
        return False, f"FFmpeg check error: {e}"


def check_ffprobe() -> tuple[bool, str]:
    """
    Check if FFprobe is installed and accessible.

    Returns:
        (success, message) tuple
    """
    try:
        result = subprocess.run(
            ["ffprobe", "-version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return True, "FFprobe is installed"
        return False, "FFprobe command failed"
    except FileNotFoundError:
        return False, "FFprobe not found in PATH"
    except subprocess.TimeoutExpired:
        return False, "FFprobe check timed out"
    except Exception as e:
        return False, f"FFprobe check error: {e}"


def check_env_var(name: str) -> tuple[bool, str]:
    """
    Check if an environment variable is set (not empty).

    Args:
        name: Environment variable name

    Returns:
        (success, message) tuple
    """
    value = os.getenv(name)
    if value and value.strip():
        return True, f"{name} is set"
    return False, f"{name} is not set or empty"


def check_writable_projects_dir() -> tuple[bool, str]:
    """
    Check if projects directory is writable.

    Returns:
        (success, message) tuple
    """
    try:
        # Ensure directory exists
        PROJECTS_DIR.mkdir(parents=True, exist_ok=True)

        # Try to create a temporary file
        test_file = PROJECTS_DIR / ".doctor_test"
        try:
            test_file.write_text("test")
            test_file.unlink()
            return True, f"Projects directory is writable: {PROJECTS_DIR}"
        except Exception as e:
            return False, f"Cannot write to projects directory: {e}"
    except Exception as e:
        return False, f"Cannot create projects directory: {e}"


def check_all() -> int:
    """
    Run all prerequisite checks and print results.

    Returns:
        Exit code: 0 if all pass, 1 if any fail
    """
    checks = [
        ("FFmpeg", check_ffmpeg),
        ("FFprobe", check_ffprobe),
        ("GEMINI_API_KEY", lambda: check_env_var("GEMINI_API_KEY")),
        ("SUNO_API_KEY", lambda: check_env_var("SUNO_API_KEY")),
        (
            "YOUTUBE_OAUTH_CREDENTIALS_PATH",
            lambda: check_env_var("YOUTUBE_OAUTH_CREDENTIALS_PATH"),
        ),
        ("Projects directory", check_writable_projects_dir),
    ]

    print("Running prerequisite checks...\n")
    all_passed = True

    for name, check_func in checks:
        success, message = check_func()
        status = "✓" if success else "✗"
        print(f"{status} {name}: {message}")
        if not success:
            all_passed = False

    print()
    if all_passed:
        print("All checks passed!")
        return 0
    else:
        print("Some checks failed. Please fix the issues above.")
        return 1


if __name__ == "__main__":
    sys.exit(check_all())

