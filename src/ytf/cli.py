"""
CLI entry point using Typer.

Commands:
- new: Create a new project
- doctor: Validate prerequisites
- plan: Generate planning data
- generate: Generate music tracks
- review: Run quality control checks
- render: Render final video
- upload: Upload to YouTube
- run: Run pipeline steps sequentially for a project
- batch: Create and run multiple projects in batch

Note: Requires Python 3.10+. The `importlib.metadata.packages_distributions` error
on Python 3.9 is expected and will be resolved by using Python 3.10+.
"""

import sys

# Check Python version early
if sys.version_info < (3, 10):
    print(
        "Error: yt-factory requires Python 3.10 or higher. "
        f"Current version: {sys.version}",
        file=sys.stderr,
    )
    sys.exit(1)

import typer

from ytf import doctor
from ytf import runner
from ytf.cli_logs import logs_app
from ytf.steps import generate, new, plan, queue, render, review, upload

app = typer.Typer(help="yt-factory: Local-first automation pipeline for music compilations")


@app.command(name="new")
def new_cmd(
    theme: str = typer.Argument(..., help="Project theme"),
    channel: str = typer.Option(..., "--channel", "-c", help="Channel ID (e.g., cafe_jazz, fantasy_tavern)"),
    minutes: int = typer.Option(None, "--minutes", "-m", help="Target duration in minutes (overrides channel default)"),
    tracks: int = typer.Option(None, "--tracks", "-t", help="Number of tracks to generate (overrides channel default)"),
    vocals: str = typer.Option("off", "--vocals", help="Vocals: 'on' or 'off'"),
    lyrics: str = typer.Option("off", "--lyrics", help="Lyrics: 'on' or 'off'"),
) -> None:
    """Create a new project."""
    if vocals not in ("on", "off"):
        typer.echo("Error: --vocals must be 'on' or 'off'", err=True)
        raise typer.Exit(1)
    if lyrics not in ("on", "off"):
        typer.echo("Error: --lyrics must be 'on' or 'off'", err=True)
        raise typer.Exit(1)

    project_id = new.create_project(theme, channel, minutes, tracks, vocals, lyrics)
    typer.echo(f"Created project: {project_id}")


@app.command(name="doctor")
def doctor_cmd() -> None:
    """Validate prerequisites (FFmpeg, env vars, writable directories)."""
    exit_code = doctor.check_all()
    raise typer.Exit(exit_code)


@app.command(name="plan")
def plan_cmd(project_id: str = typer.Argument(..., help="Project ID")) -> None:
    """Generate planning data (not implemented yet in Sprint 1)."""
    plan.run(project_id)


@app.command(name="generate")
def generate_cmd(project_id: str = typer.Argument(..., help="Project ID")) -> None:
    """Generate music tracks (not implemented yet in Sprint 1)."""
    generate.run(project_id)


@app.command(name="review")
def review_cmd(project_id: str = typer.Argument(..., help="Project ID")) -> None:
    """Run quality control checks and generate review reports."""
    review.run(project_id)


@app.command(name="render")
def render_cmd(project_id: str = typer.Argument(..., help="Project ID")) -> None:
    """Render final video (not implemented yet in Sprint 1)."""
    render.run(project_id)


@app.command(name="upload")
def upload_cmd(project_id: str = typer.Argument(..., help="Project ID")) -> None:
    """Upload to YouTube (not implemented yet in Sprint 1)."""
    upload.run(project_id)


@app.command(name="run")
def run_cmd(
    project_id: str = typer.Argument(..., help="Project ID"),
    to_step: str = typer.Option("upload", "--to", help="Target step to run up to (plan, generate, review, render, upload)"),
    from_step: str = typer.Option(None, "--from", help="Starting step (default: infer from project status)"),
) -> None:
    """Run pipeline steps sequentially for a project."""
    runner.run_project(project_id, to_step=to_step, from_step=from_step)
    typer.echo(f"Completed running steps up to: {to_step}")


@app.command(name="batch")
def batch_cmd(
    channel: str = typer.Option(..., "--channel", "-c", help="Channel ID (e.g., cafe_jazz, fantasy_tavern)"),
    count: int = typer.Option(..., "--count", "-n", help="Number of projects to create"),
    mode: str = typer.Option("full", "--mode", "-m", help="Target mode: full, render, generate, plan, review, upload"),
    theme: str = typer.Option("Batch Project", "--theme", "-t", help="Base theme (will be suffixed with index)"),
) -> None:
    """Create and run multiple projects in batch."""
    summary = runner.run_batch(
        channel_id=channel,
        count=count,
        mode=mode,
        base_theme=theme,
    )
    
    typer.echo(f"Batch completed: {summary['batch_id']}")
    typer.echo(f"Successful: {summary['successful']}/{summary['total_projects']}")
    typer.echo(f"Failed: {summary['failed']}/{summary['total_projects']}")
    typer.echo(f"Summary saved to: projects/{summary['batch_id']}_summary.json")


@app.command(name="queue")
def queue_cmd(
    action: str = typer.Argument(..., help="Action: add, ls, or run"),
    channel: str = typer.Option(None, "--channel", "-c", help="Channel ID (required for 'add')"),
    theme: str = typer.Option(None, "--theme", "-t", help="Theme (required for 'add')"),
    mode: str = typer.Option("full", "--mode", "-m", help="Target mode (required for 'add')"),
    count: int = typer.Option(1, "--count", "-n", help="Number of items to add (for 'add')"),
    limit: int = typer.Option(None, "--limit", "-l", help="Max items to process (for 'run')"),
) -> None:
    """Queue-based batch processing."""
    if action == "add":
        if not channel or not theme:
            typer.echo("Error: --channel and --theme are required for 'add'", err=True)
            raise typer.Exit(1)
        created = queue.add_queue_item(
            channel_id=channel,
            theme=theme,
            mode=mode,
            count=count,
        )
        typer.echo(f"Added {len(created)} item(s) to queue")
        for filename in created:
            typer.echo(f"  - {filename}")
    elif action == "ls":
        status = queue.list_queue()
        typer.echo("Queue status:")
        typer.echo(f"  Pending: {status['pending']}")
        typer.echo(f"  In progress: {status['in_progress']}")
        typer.echo(f"  Done: {status['done']}")
        typer.echo(f"  Failed: {status['failed']}")
    elif action == "run":
        summary = queue.run_queue(limit=limit)
        typer.echo(f"Queue run completed: {summary['run_id']}")
        typer.echo(f"Processed: {summary['processed']}")
        typer.echo(f"Successful: {summary['successful']}")
        typer.echo(f"Failed: {summary['failed']}")
        typer.echo(f"Summary saved to: queue/runs/{summary['run_id']}.json")
    else:
        typer.echo(f"Error: Unknown action '{action}'. Use 'add', 'ls', or 'run'", err=True)
        raise typer.Exit(1)

@app.command(name="logs")
def logs_cmd(
    project_id: str = typer.Argument(None, help="Project ID"),
    action: str = typer.Argument("view", help="Action: 'view' or 'summary'"),
    step: str = typer.Option(None, "--step", "-s", help="Filter to specific step"),
    json_logs: bool = typer.Option(False, "--json", help="Parse and display JSON logs"),
    errors_only: bool = typer.Option(False, "--errors-only", help="Show only ERROR level entries"),
    lines: int = typer.Option(50, "--lines", "-n", help="Number of lines to show (default: 50)"),
) -> None:
    """View project logs and summaries."""
    if action == "view":
        if not project_id:
            typer.echo("Error: project_id is required for 'view' action", err=True)
            raise typer.Exit(1)
        from ytf.cli_logs import logs_view_cmd
        logs_view_cmd(project_id, step, json_logs, errors_only, lines)
    elif action == "summary":
        if not project_id:
            typer.echo("Error: project_id is required for 'summary' action", err=True)
            raise typer.Exit(1)
        from ytf.cli_logs import logs_summary_cmd
        logs_summary_cmd(project_id, step)
    else:
        typer.echo(f"Error: Unknown action '{action}'. Use 'view' or 'summary'", err=True)
        raise typer.Exit(1)


@app.command(name="soundbank")
def soundbank_cmd(
    action: str = typer.Argument(..., help="Action: 'ls', 'add', or 'generate'"),
    sound_id: str = typer.Option(None, "--id", help="Sound ID (required for 'add' and 'generate')"),
    file_path: str = typer.Option(None, "--file", help="Path to audio file (required for 'add')"),
    name: str = typer.Option(None, "--name", help="Human-readable name (required for 'add' and 'generate')"),
    style: str = typer.Option(None, "--style", help="Music style for Suno (required for 'generate')"),
    prompt: str = typer.Option(None, "--prompt", help="Audio description for Suno (required for 'generate')"),
    description: str = typer.Option(None, "--description", help="Optional description"),
) -> None:
    """Manage global soundbank of reusable audio stems for tinnitus channel."""
    from ytf import soundbank
    
    if action == "ls":
        sounds = soundbank.list_sounds()
        if not sounds:
            typer.echo("Soundbank is empty. Use 'ytf soundbank add' or 'ytf soundbank generate' to add sounds.")
            return
        
        typer.echo(f"Soundbank ({len(sounds)} sounds):")
        for s in sounds:
            duration_min = s.duration_seconds / 60
            desc = f" - {s.description}" if s.description else ""
            typer.echo(f"  {s.sound_id}: {s.name} ({duration_min:.1f} min){desc}")
            typer.echo(f"    File: {s.filename}, Source: {s.source}")
    
    elif action == "add":
        if not sound_id or not file_path or not name:
            typer.echo("Error: --id, --file, and --name are required for 'add'", err=True)
            raise typer.Exit(1)
        
        try:
            entry = soundbank.add_sound_from_file(
                file_path=file_path,
                sound_id=sound_id,
                name=name,
                description=description,
                source="manual",
            )
            typer.echo(f"Added sound: {entry.sound_id} ({entry.name})")
            typer.echo(f"  Duration: {entry.duration_seconds / 60:.1f} minutes")
            typer.echo(f"  File: {entry.filename}")
        except Exception as e:
            typer.echo(f"Error: {e}", err=True)
            raise typer.Exit(1)
    
    elif action == "generate":
        if not sound_id or not name or not style or not prompt:
            typer.echo("Error: --id, --name, --style, and --prompt are required for 'generate'", err=True)
            raise typer.Exit(1)
        
        try:
            typer.echo(f"Generating sound via Suno: {name}...")
            entry = soundbank.generate_sound_via_suno(
                sound_id=sound_id,
                name=name,
                style=style,
                prompt=prompt,
                description=description,
            )
            typer.echo(f"Generated sound: {entry.sound_id} ({entry.name})")
            typer.echo(f"  Duration: {entry.duration_seconds / 60:.1f} minutes")
            typer.echo(f"  File: {entry.filename}")
        except Exception as e:
            typer.echo(f"Error: {e}", err=True)
            raise typer.Exit(1)
    
    else:
        typer.echo(f"Error: Unknown action '{action}'. Use 'ls', 'add', or 'generate'", err=True)
        raise typer.Exit(1)


def main() -> None:
    """Main entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()

