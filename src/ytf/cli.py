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
        "Error: yt-factory requires Python 3.10 or higher. " f"Current version: {sys.version}",
        file=sys.stderr,
    )
    sys.exit(1)

from datetime import datetime

import typer

from ytf import doctor, runner
from ytf.steps import generate, new, plan, queue, render, review, upload

app = typer.Typer(help="yt-factory: Local-first automation pipeline for music compilations")


@app.command(name="new")
def new_cmd(
    theme: str = typer.Argument(..., help="Project theme"),
    channel: str = typer.Option(
        ..., "--channel", "-c", help="Channel ID (e.g., cafe_jazz, fantasy_tavern)"
    ),
    minutes: int = typer.Option(
        None, "--minutes", "-m", help="Target duration in minutes (overrides channel default)"
    ),
    tracks: int = typer.Option(
        None, "--tracks", "-t", help="Number of tracks to generate (overrides channel default)"
    ),
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
    to_step: str = typer.Option(
        "upload", "--to", help="Target step to run up to (plan, generate, review, render, upload)"
    ),
    from_step: str = typer.Option(
        None, "--from", help="Starting step (default: infer from project status)"
    ),
) -> None:
    """Run pipeline steps sequentially for a project."""
    runner.run_project(project_id, to_step=to_step, from_step=from_step)
    typer.echo(f"Completed running steps up to: {to_step}")


@app.command(name="batch")
def batch_cmd(
    channel: str = typer.Option(
        ..., "--channel", "-c", help="Channel ID (e.g., cafe_jazz, fantasy_tavern)"
    ),
    count: int = typer.Option(..., "--count", "-n", help="Number of projects to create"),
    mode: str = typer.Option(
        "full", "--mode", "-m", help="Target mode: full, render, generate, plan, review, upload"
    ),
    theme: str = typer.Option(
        "Batch Project", "--theme", "-t", help="Base theme (will be suffixed with index)"
    ),
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


soundbank_app = typer.Typer(
    help="Manage global soundbank of reusable audio stems for tinnitus channel"
)
app.add_typer(soundbank_app, name="soundbank")


@soundbank_app.command(name="ls")
def soundbank_ls_cmd() -> None:
    """List all sounds in the soundbank."""
    from ytf import soundbank

    sounds = soundbank.list_sounds()
    if not sounds:
        typer.echo(
            "Soundbank is empty. Use 'ytf soundbank add' or 'ytf soundbank generate' to add sounds."
        )
        return

    typer.echo(f"Soundbank ({len(sounds)} sounds):")
    for sound in sounds:
        duration_min = sound.duration_seconds / 60
        desc = f" - {sound.description}" if sound.description else ""
        typer.echo(f"  {sound.sound_id}: {sound.name} ({duration_min:.1f} min){desc}")
        typer.echo(f"    File: {sound.filename}, Source: {sound.source}")
        if sound.license_type:
            commercial_status = (
                "(Commercial OK)" if sound.commercial_ok else "(Commercial use not allowed)"
            )
            typer.echo(f"    License: {sound.license_type} {commercial_status}")


@soundbank_app.command(name="add")
def soundbank_add_cmd(
    file_path: str = typer.Argument(..., help="Path to audio file to add"),
    sound_id: str = typer.Option(
        None, "--id", "-i", help="Optional sound ID (default: auto-generated)"
    ),
    name: str = typer.Option(None, "--name", "-n", help="Optional name for the sound"),
) -> None:
    """Add an existing audio file to the soundbank."""
    from pathlib import Path

    from ytf import soundbank

    if not sound_id:
        sound_id = Path(file_path).stem

    if not name:
        name = sound_id.replace("_", " ").title()

    try:
        entry = soundbank.add_sound_from_file(
            file_path=file_path,
            sound_id=sound_id,
            name=name,
            source="manual",
        )
        typer.echo(f"Added sound to soundbank: {entry.sound_id} ({entry.name})")
        if entry.license_type:
            typer.echo(
                f"  License: {entry.license_type} {'(Commercial OK)' if entry.commercial_ok else ''}"
            )
    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)


@soundbank_app.command(name="search")
def soundbank_search_cmd(
    query: str = typer.Argument(..., help="Search query"),
    limit: int = typer.Option(5, "--limit", "-l", help="Maximum results per source"),
) -> None:
    """Search for sounds on Freesound and Pixabay."""
    from ytf import soundbank

    typer.echo(f"Searching for '{query}'...\n")

    # Search Freesound
    typer.echo("=== Freesound Results ===")
    try:
        freesound_results = soundbank.search_freesound(query, limit=limit)
        if freesound_results:
            for i, result in enumerate(freesound_results, 1):
                typer.echo(f"{i}. {result['name']} (ID: {result['id']})")
                typer.echo(
                    f"   License: {result.get('license', 'N/A')} | Duration: {result.get('duration', 0):.1f}s"
                )
                typer.echo(f"   URL: {result.get('url', 'N/A')}")
        else:
            typer.echo("  No results found (or API key not set)")
    except Exception as e:
        typer.echo(f"  Error: {e}")

    typer.echo("\n=== Pixabay Results ===")
    try:
        pixabay_results = soundbank.search_pixabay(query, limit=limit)
        if pixabay_results:
            for i, result in enumerate(pixabay_results, 1):
                typer.echo(
                    f"{i}. {result.get('name', result.get('title', 'Untitled'))} (ID: {result['id']})"
                )
                typer.echo(
                    f"   License: {result.get('license', 'N/A')} | Duration: {result.get('duration', 0):.1f}s"
                )
                typer.echo(f"   URL: {result.get('url', 'N/A')}")
        else:
            typer.echo("  No results found (or API key not set)")
    except Exception as e:
        typer.echo(f"  Error: {e}")


@soundbank_app.command(name="generate")
def soundbank_generate_cmd(
    sound_id: str = typer.Argument(..., help="Sound ID"),
    query: str = typer.Option(..., "--query", "-q", help="Search query or prompt"),
    name: str = typer.Option(None, "--name", "-n", help="Optional name for the sound"),
    source: str = typer.Option(
        "auto", "--source", "-s", help="Source: 'freesound', 'pixabay', 'suno', or 'auto' (default)"
    ),
    style: str = typer.Option(None, "--style", help="Music style for Suno (default: 'Ambient')"),
) -> None:
    """Generate or download a sound from multiple sources with automatic fallback."""
    from ytf import soundbank

    if source not in ["freesound", "pixabay", "suno", "auto"]:
        typer.echo(
            f"Error: Invalid source '{source}'. Must be 'freesound', 'pixabay', 'suno', or 'auto'",
            err=True,
        )
        raise typer.Exit(1)

    if not name:
        name = sound_id.replace("_", " ").title()

    try:
        typer.echo(f"Generating sound '{name}' from {source}...")
        entry = soundbank.generate_sound(
            sound_id=sound_id,
            name=name,
            query=query,
            style=style,
            source=source,
        )
        typer.echo(f"✓ Generated sound: {entry.sound_id} ({entry.name})")
        typer.echo(f"  Source: {entry.source}")
        typer.echo(
            f"  License: {entry.license_type} {'(Commercial OK)' if entry.commercial_ok else '(Commercial use not allowed)'}"
        )
        typer.echo(f"  Duration: {entry.duration_seconds:.2f}s")
        typer.echo(f"  File: {entry.filename}")
    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)


@soundbank_app.command(name="download")
def soundbank_download_cmd(
    source: str = typer.Argument(..., help="Source: 'freesound' or 'pixabay'"),
    source_id: str = typer.Argument(
        ..., help="Source ID (Freesound sound ID or Pixabay download URL)"
    ),
    sound_id: str = typer.Option(..., "--id", "-i", help="Sound ID for soundbank"),
    name: str = typer.Option(None, "--name", "-n", help="Optional name for the sound"),
) -> None:
    """Download a sound directly from Freesound or Pixabay by ID."""

    from ytf import soundbank
    from ytf.utils.ffprobe import get_duration_seconds

    if source not in ["freesound", "pixabay"]:
        typer.echo(f"Error: Invalid source '{source}'. Must be 'freesound' or 'pixabay'", err=True)
        raise typer.Exit(1)

    if not name:
        name = sound_id.replace("_", " ").title()

    try:
        soundbank._ensure_soundbank_dir()
        filename = f"{sound_id}.mp3"
        output_path = soundbank.SOUNDBANK_DIR / filename

        if source == "freesound":
            typer.echo(f"Downloading from Freesound (ID: {source_id})...")
            metadata = soundbank.download_from_freesound(int(source_id), output_path)
            license_type = metadata.get("license")
            license_url = metadata.get("license_url")
        else:  # pixabay
            typer.echo(f"Downloading from Pixabay (URL: {source_id})...")
            metadata = soundbank.download_from_pixabay(source_id, output_path)
            license_type = "Pixabay"
            license_url = metadata.get("license_url", "https://pixabay.com/service/license/")

        # Get duration
        duration = get_duration_seconds(output_path)

        # Create entry
        entry = soundbank.SoundbankEntry(
            sound_id=sound_id,
            filename=filename,
            name=name,
            duration_seconds=duration,
            created_at=datetime.now().isoformat(),
            source=source,
            license_type=license_type,
            license_url=license_url,
            commercial_ok=True,  # Both Freesound (CC0/CC-BY) and Pixabay allow commercial use
        )

        # Add to soundbank
        soundbank_obj = soundbank._load_soundbank()
        soundbank_obj.sounds.append(entry)
        soundbank._save_soundbank(soundbank_obj)

        typer.echo(f"✓ Downloaded sound: {entry.sound_id} ({entry.name})")
        typer.echo(f"  License: {entry.license_type} (Commercial OK)")
        typer.echo(f"  Duration: {entry.duration_seconds:.2f}s")
        typer.echo(f"  File: {entry.filename}")
    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)


def main() -> None:
    """Main entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()
