# AGENTS.md (LLM Rulebook + Doc Router)

This repo is a **local-first Python CLI** project called **yt-factory**.

If you are an LLM/agent: **read this file first**, follow its rules, then open the linked docs only when you need deeper details.

Note: This file is the single source of truth for agent rules in this repo (we intentionally do not rely on `.cursorrules`).

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

---

## Context7 requirement (don’t guess APIs)
Before implementing or modifying any external API integration:
- Use **Context7** to confirm endpoint paths, auth headers, payloads, and required scopes.
- If uncertain about an API detail: **do not guess**. Fetch docs via Context7 and cite them in code comments.


