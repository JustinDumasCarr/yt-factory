# Tasks

## Implementation tasks

- [x] Copy SIASOLA starter template files into `yt-factory`:
  - `.cursor/rules/01-definition-of-done.md`
  - `.cursor/rules/02-testing.md`
  - `.cursor/rules/03-branch-only.md`
  - `VERIFY.md`
  - `specs/_templates/*.md` (6 files)
- [x] Create `scripts/verify.sh` with offline checks:
  - Python syntax (`compileall`)
  - CLI smoke (`python -m ytf --help`)
  - Schema validation (embedded Python snippet)
  - Unit tests (`pytest` if available)
- [x] Update `Makefile`:
  - Change `make test` to call `scripts/verify.sh`
  - Add `make doctor-offline` for local tool checks
- [x] Add `requirements-dev.txt` with `pytest>=8.0.0`
- [x] Create `tests/test_project_schema.py` with offline schema tests
- [x] Update `docs/DEFINITION_OF_DONE.md` with Engineering/Repo DoD section
- [x] Create `.github/workflows/ci.yml` (Python 3.11, resilient install, runs verify)
- [x] Create example spec folder `specs/2026-01-04-siasola-adoption/` with all template files

## Testing tasks

- [x] Run `scripts/verify.sh` locally and confirm it exits 0 without API keys
- [x] Verify pytest tests pass (8 tests in `test_project_schema.py`)
- [x] Confirm `make test` works offline
- [x] Confirm `make doctor-offline` works without API keys

## Documentation tasks

- [x] Update `VERIFY.md` with yt-factory-specific notes
- [x] Update `docs/DEFINITION_OF_DONE.md` with Engineering/Repo section
- [x] Create example spec folder demonstrating the contract

## Dependencies

- None (all changes are additive, no breaking changes)
