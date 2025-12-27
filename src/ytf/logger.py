"""
Dual logging: writes to both console and per-step log files.

Each step gets its own log file: projects/<id>/logs/<step>.log
All log messages also appear on console with timestamps.

Optional JSON logging: if YTF_JSON_LOGS=true, also writes structured JSON logs
to projects/<id>/logs/<step>.log.json
"""

import json
import os
import sys
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional

from ytf.project import PROJECTS_DIR
from ytf.utils.log_summary import generate_summary, save_summary


class StepLogger:
    """
    Logger that writes to both console and step-specific log file.

    Optional JSON logging: if YTF_JSON_LOGS=true, also writes structured JSON logs.

    Usage:
        with StepLogger(project_id, "plan") as log:
            log.info("Starting plan step")
            log.error("Something went wrong")
        
        # With context for structured metadata:
        with log.with_context(track_index=0, provider="suno") as ctx_log:
            ctx_log.info("Generating track")
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
        self.json_log_file = None
        self.json_log_enabled = os.getenv("YTF_JSON_LOGS", "").lower() in ("true", "1", "yes")
        self.context: dict = {}  # Current context metadata
        self.step_start_time: Optional[datetime] = None

    def _format_message(self, level: str, message: str, context: Optional[dict] = None) -> str:
        """
        Format log message with timestamp and metadata.

        Args:
            level: Log level (INFO, ERROR, etc.)
            message: Log message
            context: Optional context metadata to include

        Returns:
            Formatted log line
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        base = f"[{timestamp}] [{self.step.upper()}] [{level}] {message}"
        
        # Append context if present
        if context:
            ctx_parts = []
            for key, value in sorted(context.items()):
                if value is not None:
                    ctx_parts.append(f"{key}={value}")
            if ctx_parts:
                base += f" [{', '.join(ctx_parts)}]"
        
        return base
    
    def _format_json_log(self, level: str, message: str, context: Optional[dict] = None) -> dict:
        """
        Format log message as JSON structure.

        Args:
            level: Log level (INFO, ERROR, etc.)
            message: Log message
            context: Optional context metadata

        Returns:
            JSON-serializable dict
        """
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "step": self.step,
            "level": level,
            "message": message,
            "project_id": self.project_id,
        }
        
        # Merge context into log entry
        if context:
            log_entry.update(context)
        
        return log_entry

    def _write(self, level: str, message: str, context: Optional[dict] = None) -> None:
        """
        Write message to both console and log file (and JSON log if enabled).

        Args:
            level: Log level
            message: Log message
            context: Optional context metadata (merged with self.context)
        """
        # Merge provided context with logger context
        merged_context = {**self.context}
        if context:
            merged_context.update(context)
        
        formatted = self._format_message(level, message, merged_context if merged_context else None)

        # Write to console
        print(formatted, file=sys.stdout)

        # Write to text log file if open
        if self.log_file:
            self.log_file.write(formatted + "\n")
            self.log_file.flush()
        
        # Write to JSON log file if enabled
        if self.json_log_enabled and self.json_log_file:
            json_entry = self._format_json_log(level, message, merged_context if merged_context else None)
            self.json_log_file.write(json.dumps(json_entry) + "\n")
            self.json_log_file.flush()

    def info(self, message: str, **context) -> None:
        """Log an info message with optional context."""
        self._write("INFO", message, context if context else None)

    def error(self, message: str, **context) -> None:
        """Log an error message with optional context."""
        self._write("ERROR", message, context if context else None)

    def warning(self, message: str, **context) -> None:
        """Log a warning message with optional context."""
        self._write("WARNING", message, context if context else None)
    
    @contextmanager
    def with_context(self, **kwargs):
        """
        Context manager for adding structured metadata to log entries.
        
        Usage:
            with log.with_context(track_index=0, provider="suno") as ctx_log:
                ctx_log.info("Generating track")
        
        Args:
            **kwargs: Context metadata (track_index, provider, retry_count, duration_ms, etc.)
        
        Yields:
            StepLogger instance with context applied
        """
        # Save current context
        old_context = self.context.copy()
        # Update with new context
        self.context.update(kwargs)
        try:
            yield self
        finally:
            # Restore old context
            self.context = old_context

    def __enter__(self):
        """Context manager entry: open log file."""
        # Ensure log directory exists
        self.log_file_path.parent.mkdir(parents=True, exist_ok=True)

        # Open text log file in append mode
        self.log_file = open(self.log_file_path, "a", encoding="utf-8")
        
        # Open JSON log file if enabled
        if self.json_log_enabled:
            json_log_path = self.log_file_path.parent / f"{self.step}.log.json"
            self.json_log_file = open(json_log_path, "a", encoding="utf-8")
        
        # Record step start time
        self.step_start_time = datetime.now()

        # Log session start
        self.info(f"Starting {self.step} step for project {self.project_id}")

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit: close log file, log exceptions."""
        # Calculate step duration
        step_duration_ms = None
        if self.step_start_time:
            duration = datetime.now() - self.step_start_time
            step_duration_ms = int(duration.total_seconds() * 1000)
        
        if exc_type is not None:
            # Log exception details
            import traceback

            self.error(f"Exception in {self.step} step: {exc_val}", duration_ms=step_duration_ms)
            if self.log_file:
                self.log_file.write("\n" + "=" * 80 + "\n")
                self.log_file.write("FULL TRACEBACK:\n")
                self.log_file.write("=" * 80 + "\n")
                self.log_file.write(traceback.format_exc())
                self.log_file.write("\n")
                self.log_file.flush()
        else:
            # Log successful completion with duration
            self.info(f"Completed {self.step} step", duration_ms=step_duration_ms)

        if self.log_file:
            self.log_file.close()
            self.log_file = None
        
        if self.json_log_file:
            self.json_log_file.close()
            self.json_log_file = None
        
        # Generate summary after step completes
        try:
            summary = generate_summary(self.project_id, self.step)
            save_summary(self.project_id, self.step, summary)
        except Exception:
            # Don't fail if summary generation fails
            pass

        # Don't suppress exceptions
        return False

