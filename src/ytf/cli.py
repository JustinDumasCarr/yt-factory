"""
CLI entry point using Typer.

Commands:
- new: Create a new project
- doctor: Validate prerequisites
- plan: Generate planning data (skeleton in Sprint 1)
- generate: Generate music tracks (skeleton in Sprint 1)
- render: Render final video (skeleton in Sprint 1)
- upload: Upload to YouTube (skeleton in Sprint 1)
"""

import typer

from ytf import doctor
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

if __name__ == "__main__":
    app()

