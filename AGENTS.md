# AGENTS.md (LLM Rulebook + Doc Router)

This repo is a **local-first Python CLI** project called **yt-factory**.

If you are an LLM/agent: **read this file first**, follow its rules, then open the linked docs only when you need deeper details.

Note: This file is the only source of truth for agent rules in this repo (we intentionally do not rely on `.cursorrules`).

---

## Non-negotiables (v1 constraints)
- **No database in v1.** (No hidden state; do not add SQLite/Postgres/etc.)
- **No Docker requirement** for local development.
- **No web UI in v1.**
- **Local-first, file-based state**: `projects/<project_id>/project.json` is the **single source of truth**.

---

## Core invariants (must preserve)
- **Step-based pipeline**: `new → plan → generate → review → render → upload`.
- **Every step writes a dedicated log file** under `projects/<id>/logs/`.
- **Failures must be visible**:
  - Write a clear error to `project.json.status.last_error` (message + step + stack).
  - Write **full traceback** to the step log.
  - Persist **provider raw errors** (truncate if needed, but don’t hide them).
- **No scattered network calls**: keep external API calls centralized in provider modules / provider clients.

---

## Task execution protocol (required)

This repo uses a company-wide agent system with ClickUp as the execution queue.

### Source of truth
- Tasks are selected from ClickUp only.
- `docs/TASKS.md` is an archive/reference and MUST NOT be used as the execution queue.

### Eligibility (agent may start work only if ALL are true)
- Task is in a ClickUp Folder whose name starts with: `Execution –`
- Task is in a ClickUp List named exactly: `Execution`
- Task status is exactly: `READY`
- Task body includes: Goal, Scope/Allowed, Acceptance Criteria, Verify commands

If any requirement is missing:
- Comment what is missing
- Move task to `SPEC NEEDED`
- Stop

### Workflow
1) Pull the next eligible task from ClickUp (highest priority, then oldest).
2) Create a branch named: `task/<TASK_ID>` (or `clickup/<TASK_ID>`)
3) Implement ONLY what the task requests (no scope creep).
4) Run all Verify commands exactly as written.
5) If Verify passes:
   - Open a PR titled: `<TASK_ID> <short title>`
   - Move task to `NEEDS REVIEW`
   - Paste verification output in the PR description or task comment
6) If Verify fails after 3 attempts:
   - Paste logs/output
   - Move task to `BLOCKED`
   - Stop

### Local verification
Preferred verification entrypoint:
- `make test`

---

## Code structure rules
- Keep modules small and boring: **one file per step** under `src/ytf/steps/`.
- Providers are isolated under `src/ytf/providers/`:
  - **Do not mix provider logic into render/upload steps**.
- Use typed config objects and **validate `project.json` before running a step**.
- Prefer explicit exceptions and clear error messages over silent fallback behavior.

---

## Debugging contract (required behavior)
When anything fails:
- Update `project.json.status.last_error` with:
  - `step`, `message`, `stack`, `at` (and if available: `kind`, `provider`, `raw`)
- Ensure the step log contains the full traceback.
- Do **not** delete partial outputs; keep them for debugging and resuming.

---

## Definition of Done (strict)

A task is considered done ONLY if:
- All its listed Verify commands succeed
- `project.json` validation passes
- No core invariants are violated
- TASKS.md is updated in the same PR

If any Verify command fails, the task is NOT done.

---
## Canonical verification command

Preferred verification entrypoint:
- `make test`

If task-specific verification exists, it will be listed in TASKS.md.

---

## Documentation router (open these when relevant)

### Start here
- `docs/00_OVERVIEW.md`: system overview + default behaviors
- `docs/01_WORKFLOW.md`: step semantics, lifecycle, and how the pipeline is expected to work

### State & schema
- `docs/03_PROJECT_SCHEMA.md`: `project.json` shape + project folder layout

### Logging & recovery
- `docs/04_LOGGING_AND_DEBUGGING.md`: log formats, summaries, how to inspect failures
- `docs/ERRORS_AND_RECOVERY.md`: failure playbooks + deterministic recovery paths

### Providers & integrations (read before changing APIs)
- `docs/05_PROVIDERS_GEMINI.md`: Gemini integration details
- `docs/06_PROVIDERS_SUNO.md` and `docs/refs/SUNO_API.md`: Suno integration details
- `docs/08_YOUTUBE_UPLOAD.md`: YouTube upload integration details

### Planning work (what to do next)
- `docs/ROADMAP.md`: **milestone-level outcomes** (where we’re heading / what’s shipped)
- `docs/TASKS.md`: **short-term execution list** (what we’re doing next; keep it small and actionable)
- `docs/DECISIONS.md`: why decisions were made (prevents rework and re-arguing)

---

## Context7 requirement (don’t guess APIs)
Before implementing or modifying any external API integration:
- Use **Context7** to confirm endpoint paths, auth headers, payloads, and required scopes.
- If uncertain about an API detail: **do not guess**. Fetch docs via Context7 and cite them in code comments.


