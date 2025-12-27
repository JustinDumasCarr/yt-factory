"""
Log summary generation: parse step logs and generate error summaries.

Generates structured summaries with error counts, retry statistics, duration breakdown,
and provider-specific error analysis.
"""

import json
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Optional

from ytf.project import PROJECTS_DIR


def parse_text_log(log_path: Path) -> list[dict]:
    """
    Parse text log file and extract structured information.

    Args:
        log_path: Path to log file

    Returns:
        List of parsed log entries with level, message, timestamp, context
    """
    entries = []
    if not log_path.exists():
        return entries
    
    # Pattern: [timestamp] [STEP] [LEVEL] message [context]
    pattern = re.compile(
        r'\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\] \[(\w+)\] \[(\w+)\] (.+?)(?: \[(.+)\])?$'
    )
    
    with open(log_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            
            match = pattern.match(line)
            if match:
                timestamp_str, step, level, message, context_str = match.groups()
                entry = {
                    "timestamp": timestamp_str,
                    "step": step.lower(),
                    "level": level,
                    "message": message,
                }
                
                # Parse context if present
                if context_str:
                    context = {}
                    for part in context_str.split(", "):
                        if "=" in part:
                            key, value = part.split("=", 1)
                            # Try to parse numeric values
                            try:
                                if "." in value:
                                    context[key] = float(value)
                                else:
                                    context[key] = int(value)
                            except ValueError:
                                context[key] = value
                    entry["context"] = context
                
                entries.append(entry)
    
    return entries


def parse_json_log(log_path: Path) -> list[dict]:
    """
    Parse JSON log file.

    Args:
        log_path: Path to JSON log file

    Returns:
        List of log entries
    """
    entries = []
    if not log_path.exists():
        return entries
    
    with open(log_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                entries.append(entry)
            except json.JSONDecodeError:
                continue
    
    return entries


def generate_summary(project_id: str, step: str) -> dict:
    """
    Generate error summary for a step.

    Args:
        project_id: Project ID
        step: Step name

    Returns:
        Summary dict with error counts, retry stats, duration breakdown, etc.
    """
    project_dir = PROJECTS_DIR / project_id
    logs_dir = project_dir / "logs"
    
    # Try JSON log first, fall back to text log
    json_log_path = logs_dir / f"{step}.log.json"
    text_log_path = logs_dir / f"{step}.log"
    
    entries = []
    if json_log_path.exists():
        entries = parse_json_log(json_log_path)
    elif text_log_path.exists():
        entries = parse_text_log(text_log_path)
    else:
        return {
            "project_id": project_id,
            "step": step,
            "status": "no_logs",
            "error": "Log file not found",
        }
    
    if not entries:
        return {
            "project_id": project_id,
            "step": step,
            "status": "empty",
            "error": "Log file is empty",
        }
    
    # Analyze entries
    error_count = defaultdict(int)
    error_by_type = defaultdict(int)
    error_by_provider = defaultdict(int)
    retry_count = 0
    retry_success_count = 0
    track_failures = []
    durations = []
    provider_durations = defaultdict(list)
    
    for entry in entries:
        level = entry.get("level", "").upper()
        message = entry.get("message", "")
        context = entry.get("context", {})
        
        # Count errors
        if level == "ERROR":
            error_count["total"] += 1
            
            # Classify error type from message/context
            if "auth" in message.lower() or "401" in message or "403" in message:
                error_by_type["auth"] += 1
            elif "rate_limit" in message.lower() or "429" in message or "quota" in message.lower():
                error_by_type["rate_limit"] += 1
            elif "timeout" in message.lower():
                error_by_type["timeout"] += 1
            elif "validation" in message.lower() or "invalid" in message.lower():
                error_by_type["validation"] += 1
            elif "ffmpeg" in message.lower():
                error_by_type["ffmpeg"] += 1
            else:
                error_by_type["unknown"] += 1
            
            # Provider-specific errors
            provider = context.get("provider") or entry.get("provider")
            if provider:
                error_by_provider[provider] += 1
            
            # Track failures (for generate step)
            track_index = context.get("track_index") or entry.get("track_index")
            if track_index is not None:
                track_failures.append({
                    "track_index": track_index,
                    "message": message,
                    "provider": provider,
                })
        
        # Count retries
        if "retry" in message.lower() or context.get("retry_count"):
            retry_count += 1
            # Check if retry was successful (next entry is success)
            # This is a simple heuristic - could be improved
        
        # Collect durations
        duration_ms = context.get("duration_ms") or entry.get("duration_ms")
        if duration_ms:
            durations.append(duration_ms)
            provider = context.get("provider") or entry.get("provider")
            if provider:
                provider_durations[provider].append(duration_ms)
    
    # Calculate statistics
    summary = {
        "project_id": project_id,
        "step": step,
        "status": "success" if error_count["total"] == 0 else "failed",
        "timestamp": datetime.now().isoformat(),
        "total_entries": len(entries),
        "errors": {
            "total": error_count["total"],
            "by_type": dict(error_by_type),
            "by_provider": dict(error_by_provider),
        },
        "retries": {
            "total": retry_count,
            "success_after_retry": retry_success_count,  # TODO: implement proper tracking
        },
        "durations": {
            "total_ms": sum(durations) if durations else None,
            "avg_ms": sum(durations) / len(durations) if durations else None,
            "min_ms": min(durations) if durations else None,
            "max_ms": max(durations) if durations else None,
            "by_provider": {
                provider: {
                    "total_ms": sum(durs),
                    "avg_ms": sum(durs) / len(durs),
                    "count": len(durs),
                }
                for provider, durs in provider_durations.items()
            },
        },
    }
    
    # Add track failures if present
    if track_failures:
        summary["track_failures"] = track_failures
    
    return summary


def save_summary(project_id: str, step: str, summary: dict) -> Path:
    """
    Save summary to JSON file.

    Args:
        project_id: Project ID
        step: Step name
        summary: Summary dict

    Returns:
        Path to saved summary file
    """
    project_dir = PROJECTS_DIR / project_id
    logs_dir = project_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    
    summary_path = logs_dir / f"{step}_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    
    return summary_path

