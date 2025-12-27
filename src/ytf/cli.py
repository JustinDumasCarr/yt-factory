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
from ytf.steps import generate, new, plan, render, review, upload

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

def main() -> None:
    """Main entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()

