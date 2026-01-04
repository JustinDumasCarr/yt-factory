# Acceptance Criteria

## Must have

- [x] `scripts/verify.sh` exists and runs offline (exits 0 without API keys)
- [x] `scripts/verify.sh` includes: syntax check, CLI smoke, schema validation, pytest
- [x] At least one offline unit test exists (`tests/test_project_schema.py`)
- [x] `Makefile` `make test` is offline-safe (does not run `ytf doctor`)
- [x] `make doctor-offline` exists for local tool checks (no API keys)
- [x] Cursor rules added: `01-definition-of-done.md`, `02-testing.md`, `03-branch-only.md`
- [x] `VERIFY.md` documents the verify entrypoint
- [x] `specs/_templates/` contains all 6 template files
- [x] `docs/DEFINITION_OF_DONE.md` includes Engineering/Repo DoD section
- [x] `.github/workflows/ci.yml` exists and runs `scripts/verify.sh` on pull_request

## Should have

- [x] Example spec folder `specs/2026-01-04-siasola-adoption/` demonstrates the contract
- [x] `evidence.md` contains real verify output (not placeholder)
- [x] CI uses Python 3.11 (not hardcoded 3.10)
- [x] CI install step is resilient (handles missing `requirements.txt`)

## Nice to have

- [x] `requirements-dev.txt` separates dev dependencies cleanly

## Testing

- [x] Tests required (pytest unit tests for schema validation)
- [ ] Tests waived (N/A)

## Definition of done

- [x] Acceptance criteria met
- [x] Verification passes (`scripts/verify.sh` exits 0)
- [x] Evidence documented (this `evidence.md` file)
