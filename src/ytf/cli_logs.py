"""
CLI commands for viewing logs and summaries.
"""

import json

import typer

from ytf.project import PROJECTS_DIR
from ytf.utils.log_summary import generate_summary, parse_json_log, parse_text_log

logs_app = typer.Typer(help="View project logs and summaries")


@logs_app.command(name="view")
def logs_view_cmd(
    project_id: str = typer.Argument(..., help="Project ID"),
    step: str = typer.Option(
        None,
        "--step",
        "-s",
        help="Filter to specific step (plan, generate, review, render, upload)",
    ),
    json_logs: bool = typer.Option(False, "--json", help="Parse and display JSON logs"),
    errors_only: bool = typer.Option(False, "--errors-only", help="Show only ERROR level entries"),
    lines: int = typer.Option(50, "--lines", "-n", help="Number of lines to show (default: 50)"),
) -> None:
    """View log entries for a project."""
    project_dir = PROJECTS_DIR / project_id
    logs_dir = project_dir / "logs"

    if not logs_dir.exists():
        typer.echo(f"Error: Logs directory not found for project {project_id}", err=True)
        raise typer.Exit(1)

    # Determine which steps to show
    if step:
        steps = [step]
    else:
        steps = ["plan", "generate", "review", "render", "upload"]

    entries_shown = 0

    for step_name in steps:
        if json_logs:
            log_path = logs_dir / f"{step_name}.log.json"
            if not log_path.exists():
                continue
            entries = parse_json_log(log_path)
        else:
            log_path = logs_dir / f"{step_name}.log"
            if not log_path.exists():
                continue
            entries = parse_text_log(log_path)

        if not entries:
            continue

        # Filter by errors if requested
        if errors_only:
            entries = [e for e in entries if e.get("level", "").upper() == "ERROR"]

        # Show last N entries
        entries = entries[-lines:]

        if entries:
            typer.echo(f"\n=== {step_name.upper()} ===")

            for entry in entries:
                if json_logs:
                    # Pretty print JSON entry
                    timestamp = entry.get("timestamp", "")
                    level = entry.get("level", "")
                    message = entry.get("message", "")
                    context = {
                        k: v
                        for k, v in entry.items()
                        if k not in ("timestamp", "step", "level", "message", "project_id")
                    }

                    context_str = ""
                    if context:
                        context_parts = [f"{k}={v}" for k, v in sorted(context.items())]
                        context_str = f" [{', '.join(context_parts)}]"

                    typer.echo(f"[{timestamp}] [{level}] {message}{context_str}")
                else:
                    # Show text log line as-is
                    log_path = logs_dir / f"{step_name}.log"
                    with open(log_path, encoding="utf-8") as f:
                        all_lines = f.readlines()
                        # Show last N lines
                        for line in all_lines[-lines:]:
                            typer.echo(line.rstrip())
                    break  # Only show one step's text log

            entries_shown += len(entries)

    if entries_shown == 0:
        typer.echo(f"No log entries found for project {project_id}")


@logs_app.command(name="summary")
def logs_summary_cmd(
    project_id: str = typer.Argument(..., help="Project ID"),
    step: str = typer.Option(
        None,
        "--step",
        "-s",
        help="Show summary for specific step (plan, generate, review, render, upload)",
    ),
) -> None:
    """Display error summary for a project."""
    project_dir = PROJECTS_DIR / project_id
    logs_dir = project_dir / "logs"

    if not logs_dir.exists():
        typer.echo(f"Error: Logs directory not found for project {project_id}", err=True)
        raise typer.Exit(1)

    # Determine which steps to show
    if step:
        steps = [step]
    else:
        steps = ["plan", "generate", "review", "render", "upload"]

    for step_name in steps:
        summary_path = logs_dir / f"{step_name}_summary.json"

        if summary_path.exists():
            with open(summary_path, encoding="utf-8") as f:
                summary = json.load(f)
        else:
            # Generate summary on the fly
            summary = generate_summary(project_id, step_name)

        if summary.get("status") == "no_logs":
            continue

        typer.echo(f"\n=== {step_name.upper()} Summary ===")
        typer.echo(f"Status: {summary.get('status', 'unknown')}")
        typer.echo(f"Total entries: {summary.get('total_entries', 0)}")

        errors = summary.get("errors", {})
        if errors.get("total", 0) > 0:
            typer.echo(f"\nErrors: {errors['total']}")
            if errors.get("by_type"):
                typer.echo("  By type:")
                for error_type, count in sorted(errors["by_type"].items()):
                    typer.echo(f"    {error_type}: {count}")
            if errors.get("by_provider"):
                typer.echo("  By provider:")
                for provider, count in sorted(errors["by_provider"].items()):
                    typer.echo(f"    {provider}: {count}")

        retries = summary.get("retries", {})
        if retries.get("total", 0) > 0:
            typer.echo(f"\nRetries: {retries['total']}")

        durations = summary.get("durations", {})
        if durations.get("avg_ms"):
            typer.echo("\nDurations:")
            typer.echo(f"  Average: {durations['avg_ms']:.0f}ms")
            typer.echo(f"  Total: {durations['total_ms']:.0f}ms")
            if durations.get("by_provider"):
                typer.echo("  By provider:")
                for provider, stats in durations["by_provider"].items():
                    typer.echo(
                        f"    {provider}: {stats['avg_ms']:.0f}ms avg ({stats['count']} calls)"
                    )

        track_failures = summary.get("track_failures", [])
        if track_failures:
            typer.echo(f"\nTrack failures: {len(track_failures)}")
            for failure in track_failures[:5]:  # Show first 5
                typer.echo(f"  Track {failure['track_index']}: {failure['message'][:60]}")
