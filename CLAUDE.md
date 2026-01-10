# yt-factory

Local-first automation pipeline for YouTube music compilations.

## Quick Start

**On session start:**
1. Check Vibe-Kanban: `list_projects` → `list_tasks`
2. Read this file and `TASKS.md`

## Project Structure

```
yt-factory/
├── src/ytf/                 # Main source code
│   ├── cli.py              # Typer CLI entry point
│   ├── providers/          # External API integrations (Suno, Gemini, YouTube)
│   ├── steps/              # Pipeline steps (new, plan, generate, review, render, upload)
│   ├── tools/              # CLI utilities (tasks)
│   └── utils/              # Helpers (ffmpeg, ffprobe, qc, retry)
├── docs/                   # Documentation
│   ├── architecture/       # System design docs
│   ├── workflow/           # Pipeline and usage docs
│   ├── providers/          # External service integration
│   └── future/             # Future plans
├── tests/                  # pytest tests
├── channels/               # Channel YAML configs
├── scripts/                # Verification scripts
└── projects/               # Project output folders (gitignored)
```

## Tech Stack

| Layer | Choice |
|-------|--------|
| CLI | Typer |
| Models | Pydantic |
| Logging | StepLogger (dual console/file) |
| Tests | pytest |
| LLM | Gemini |
| Music | Suno API |
| Video | FFmpeg |
| Upload | YouTube Data API |

## Key Commands

```bash
# Setup
pip install -e .
ytf doctor

# Pipeline
ytf new "theme" --channel cafe_jazz
ytf run <project_id> --to render
ytf queue add --channel cafe_jazz --theme "Night Jazz" --count 3
ytf queue run

# Verification
make test
make format
make lint
```

## Agents & Skills

**On every prompt**, check if a specialized agent fits:
- Research → `general-purpose` or `Explore`
- Planning → `Plan`
- Testing → `EvidenceQA`
- Python dev → `engineering-senior-developer`

**Run in background** when task is self-contained and doesn't need immediate results.

## Autonomous Rules

**Proceed when:**
- Task has clear acceptance criteria
- Tests pass (`make test`)

**Stop and ask when:**
- API keys needed (Suno, Gemini, YouTube)
- External tool required
- Cost implications

## Task Management

**Two systems, two purposes:**

| System | Source of Truth For |
|--------|---------------------|
| **Vibe-Kanban** | Task STATUS (todo → inprogress → done) |
| **TASKS.md** | Task DETAILS (acceptance criteria, tests, blocking conditions) |

**Workflow:**
1. Starting a task → Update vibe-kanban status to `inprogress`
2. Finishing a task → Update vibe-kanban status to `done`
3. Before commits → Run `/sync-tasks` to update TASKS.md from vibe-kanban

**Rules:**
- Always update vibe-kanban status FIRST (it's the source of truth)
- TASKS.md gets updated via sync (keeps git history clean)
- New tasks: Add to vibe-kanban, then add details to TASKS.md

## Vibe-Kanban

- Project ID: `a076cc8b-8555-4d31-9eff-60c7d7b16b2b`
- `list_tasks` - See all tasks
- `update_task` - Change status (todo/inprogress/done)
- `/sync-tasks` - Sync status to TASKS.md

## Key Docs

| Doc | Purpose |
|-----|---------|
| `TASKS.md` | Current tasks with acceptance criteria |
| `ROADMAP.md` | Full development roadmap |
| `docs/README.md` | Documentation index |
| `docs/workflow/pipeline.md` | Pipeline workflow reference |
| `docs/architecture/system-design.md` | System architecture |
