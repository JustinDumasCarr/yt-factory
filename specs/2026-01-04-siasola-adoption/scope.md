# Scope

## In scope

- [x] Copy SIASOLA starter template files (Cursor rules, VERIFY.md, specs templates)
- [x] Implement offline `scripts/verify.sh` (syntax, CLI smoke, schema validation, pytest)
- [x] Add `requirements-dev.txt` with pytest
- [x] Add at least one offline unit test (`tests/test_project_schema.py`)
- [x] Update `Makefile` to make `make test` offline-safe (remove `ytf doctor`, add `doctor-offline`)
- [x] Update `docs/DEFINITION_OF_DONE.md` with Engineering/Repo DoD section
- [x] Add `.github/workflows/ci.yml` (Python 3.11, resilient dependency install)
- [x] Create example spec folder `specs/2026-01-04-siasola-adoption/` with all template files

## Out of scope

- Changes to core business logic (only touched `Makefile` and added tests)
- Modifying existing `AGENTS.md` ClickUp protocol (kept as-is, SIASOLA rules are additive)
- Adding new runtime dependencies (pytest is dev-only)
- Requiring FFmpeg/FFprobe in verify (kept offline-only)

## Boundaries

- Verify must not require API keys (Suno/Gemini/YouTube)
- Verify must not make network calls
- All changes are additive (no breaking changes to existing workflows)
- CI uses Python 3.11 (single version, not a matrix)
