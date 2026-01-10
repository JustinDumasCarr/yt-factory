# New Project

Create a new yt-factory project for music compilation generation.

## When to Use
- When user wants to create a new YouTube music compilation
- When testing the pipeline

## Usage

```bash
ytf new "<theme>" --channel <channel_id> [--minutes N] [--tracks N] [--vocals on|off]
```

## Available Channels

Check the `channels/` directory for available channel profiles:

| Channel ID | Description |
|------------|-------------|
| `cafe_jazz` | Jazz music for cafe ambiance |
| `dnb_focus` | Drum and bass for focus/work |
| `fantasy_reading` | Fantasy music for reading |
| `fantasy_tavern` | Medieval tavern ambiance |
| `lofi_study` | Lo-fi beats for studying |
| `sleep_ambience` | Ambient sounds for sleep |
| `tinnitus_relief` | Sounds for tinnitus relief |

## Examples

### Basic Project
```bash
ytf new "Evening Relaxation" --channel cafe_jazz
```

### Custom Duration
```bash
ytf new "Night Focus Session" --channel dnb_focus --minutes 60 --tracks 15
```

### With Vocals
```bash
ytf new "Upbeat Cafe Vibes" --channel cafe_jazz --vocals on
```

### Short Test Project
```bash
ytf new "Quick Test" --channel cafe_jazz --minutes 10 --tracks 2
```

## After Creation

The command will output a project ID. Use it to run the pipeline:

```bash
# Run full pipeline
ytf run <project_id>

# Run up to a specific step
ytf run <project_id> --to render

# Run individual steps
ytf plan <project_id>
ytf generate <project_id>
ytf review <project_id>
ytf render <project_id>
ytf upload <project_id>
```

## Project Output

Created project will be at `projects/<project_id>/` containing:
- `project.json` - Project state and configuration
- `tracks/` - Generated audio files
- `assets/` - Background images, thumbnails
- `output/` - Final rendered video
- `logs/` - Step logs

## Notes

- Theme should be descriptive (used for Gemini prompts)
- Channel determines style, duration defaults, metadata templates
- Vocals default depends on channel profile
- Projects are idempotent - re-running steps is safe
