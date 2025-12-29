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

Unless explicitly instructed otherwise, do the following:

1) Open `docs/TASKS.md`
2) Select the **first unchecked task** (`- [ ]`) in order
3) Implement only that task
4) Run all Verify commands listed for the task
5) If verification passes:
   - Mark the task as completed (`[x]`)
   - (Optional) If you are using a GitHub workflow, open a PR with the task ID in the title
6) If verification fails:
   - Do NOT mark the task complete
   - (Optional) If you are using a GitHub workflow, fix or report failure clearly in the PR description

Do not skip tasks.
Do not combine multiple tasks in one PR unless explicitly instructed.

Preferred interface (when available):
- Use `make next`, `make verify TASK=T###`, and `make done TASK=T### FORCE=1` to drive the loop.

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


