"""
Dual logging: writes to both console and per-step log files.

Each step gets its own log file: projects/<id>/logs/<step>.log
All log messages also appear on console with timestamps.
"""

import sys
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

from ytf.project import PROJECTS_DIR


class StepLogger:
    """
    Logger that writes to both console and step-specific log file.

    Usage:
        with StepLogger(project_id, "plan") as log:
            log.info("Starting plan step")
            log.error("Something went wrong")
    """

    def __init__(self, project_id: str, step: str):
        """
        Initialize logger for a specific project and step.

        Args:
            project_id: Project ID
            step: Step name (plan, generate, render, upload)
        """
        self.project_id = project_id
        self.step = step
        self.log_file_path = PROJECTS_DIR / project_id / "logs" / f"{step}.log"
        self.log_file = None

    def _format_message(self, level: str, message: str) -> str:
        """
        Format log message with timestamp and metadata.

        Args:
            level: Log level (INFO, ERROR, etc.)
            message: Log message

        Returns:
            Formatted log line
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return f"[{timestamp}] [{self.step.upper()}] [{level}] {message}"

    def _write(self, level: str, message: str) -> None:
        """
        Write message to both console and log file.

        Args:
            level: Log level
            message: Log message
        """
        formatted = self._format_message(level, message)

        # Write to console
        print(formatted, file=sys.stdout)

        # Write to log file if open
        if self.log_file:
            self.log_file.write(formatted + "\n")
            self.log_file.flush()

    def info(self, message: str) -> None:
        """Log an info message."""
        self._write("INFO", message)

    def error(self, message: str) -> None:
        """Log an error message."""
        self._write("ERROR", message)

    def warning(self, message: str) -> None:
        """Log a warning message."""
        self._write("WARNING", message)

    def __enter__(self):
        """Context manager entry: open log file."""
        # Ensure log directory exists
        self.log_file_path.parent.mkdir(parents=True, exist_ok=True)

        # Open log file in append mode
        self.log_file = open(self.log_file_path, "a", encoding="utf-8")

        # Log session start
        self.info(f"Starting {self.step} step for project {self.project_id}")

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit: close log file, log exceptions."""
        if exc_type is not None:
            # Log exception details
            import traceback

            self.error(f"Exception in {self.step} step: {exc_val}")
            if self.log_file:
                self.log_file.write("\n" + "=" * 80 + "\n")
                self.log_file.write("FULL TRACEBACK:\n")
                self.log_file.write("=" * 80 + "\n")
                self.log_file.write(traceback.format_exc())
                self.log_file.write("\n")
                self.log_file.flush()

        if self.log_file:
            self.log_file.close()
            self.log_file = None

        # Don't suppress exceptions
        return False

