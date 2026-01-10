# yt-factory Tasks

**Status**: Active Development
**Last Updated**: January 2026

---

## How Claude Should Use This File

### Autonomous Work Rules

**Proceed autonomously when:**
1. Task has clear acceptance criteria below
2. All dependencies are met (check with tests)
3. Tests can be run to verify success (`make test`)
4. No external accounts/services needed

**STOP and notify user when:**
1. API key or credentials needed
2. External tool required
3. Test fails after 2 attempts
4. Ambiguous requirements
5. Cost implications (API calls that cost money)

### On Session Start

1. Read this file first
2. Check current phase and next pending task
3. Run `make test` to confirm state
4. Proceed with next task or notify user if blocked

---

## Current Tasks

### Refactor: Adopt spinolaa conventions

**Description**: Refactor project to follow spinolaa conventions while keeping yt-factory's strengths.

**Status**: In Progress

**Acceptance Criteria**:
- [ ] CLAUDE.md exists at project root
- [ ] ROADMAP.md exists at project root
- [ ] TASKS.md exists at project root with acceptance criteria format
- [ ] .claude/commands/ has 3 commands (sync-tasks, verify, new-project)
- [ ] pyproject.toml has black + ruff configuration
- [ ] make format runs without errors
- [ ] make lint runs without errors
- [ ] docs/ reorganized by category (architecture/, workflow/, providers/)
- [ ] docs/README.md index exists
- [ ] TESTING.md exists
- [ ] All existing tests pass (`make test`)
- [ ] CLI still works (`ytf --help`)

**Test Instructions**:
```bash
# Verify all changes
make test
make format
make lint
ytf --help
```

**Can Claude Do Autonomously?**: Yes

---

## Archive (Completed)

<details>
<summary>Click to expand completed tasks</summary>

### A. Scaffolding
- [x] Create repo structure: `src/`, `docs/`, `projects/`
- [x] Add `.env.example`
- [x] Add `docs/ROADMAP.md` and `docs/TASKS.md`

### B. Project state + logging
- [x] Implement project folder creation and id generation
- [x] Implement read/write helpers for `project.json`
- [x] Implement per-step logs
- [x] Implement status updates + last error persistence

### C. CLI command skeleton
- [x] Implement CLI entry and commands: `new`, `plan`, `generate`, `render`, `upload`
- [x] Implement `ytf doctor` command

### D. Gemini provider
- [x] Implement Gemini client wrapper
- [x] Implement `plan` step
- [x] Add prompt templates and constraints

### E. Suno provider
- [x] Implement Suno client wrapper
- [x] Implement polling + download
- [x] Compute duration for downloaded tracks

### F. Rendering (FFmpeg)
- [x] Implement track filtering
- [x] Implement loudness normalization
- [x] Implement static image mux to MP4
- [x] Generate chapters and description files
- [x] Implement background image generation with Gemini
- [x] Implement thumbnail creation with text overlay
- [x] T006 Roman inscription thumbnail text

### G. YouTube upload
- [x] Implement OAuth token caching
- [x] Implement resumable upload
- [x] Apply metadata
- [x] Persist YouTube results to project.json
- [x] Auto thumbnail upload
- [x] Idempotent upload behavior

### H. Reliability + throughput
- [x] Channel-driven workflow
- [x] `approved.txt` support
- [x] Auto-filter bad tracks (QC step)
- [x] Review/QC step
- [x] Retry/backoff wrapper
- [x] `ytf run <id>` command
- [x] `ytf batch` command
- [x] Queue-based batch processing v2

</details>
