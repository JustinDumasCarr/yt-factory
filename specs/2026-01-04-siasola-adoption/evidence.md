# Evidence

## Verification results

```
==========================================
VERIFICATION
==========================================

Checking Python syntax...
Testing CLI (--help)...
Testing project.json schema validation...
Schema validation: OK
Running unit tests...
........                                                                 [100%]
8 passed in 0.07s

==========================================
VERIFY PASSED
==========================================
```

**Command run**: `PY=./venv/bin/python bash scripts/verify.sh`  
**Exit code**: 0  
**Date**: 2026-01-04

## Acceptance criteria status

- [x] Criterion 1: ✅ PASS - `scripts/verify.sh` exists and runs offline
- [x] Criterion 2: ✅ PASS - Verify includes syntax, CLI smoke, schema validation, pytest
- [x] Criterion 3: ✅ PASS - At least one offline unit test exists (8 tests in `test_project_schema.py`)
- [x] Criterion 4: ✅ PASS - `Makefile` `make test` is offline-safe
- [x] Criterion 5: ✅ PASS - `make doctor-offline` exists
- [x] Criterion 6: ✅ PASS - Cursor rules added
- [x] Criterion 7: ✅ PASS - `VERIFY.md` documents verify entrypoint
- [x] Criterion 8: ✅ PASS - `specs/_templates/` contains all 6 template files
- [x] Criterion 9: ✅ PASS - `docs/DEFINITION_OF_DONE.md` includes Engineering/Repo DoD
- [x] Criterion 10: ✅ PASS - `.github/workflows/ci.yml` exists

## Test results

**Unit tests**: 8 passed in 0.07s
- `test_minimal_project_creation` ✅
- `test_project_with_all_fields` ✅
- `test_plan_prompt_backwards_compatibility` ✅
- `test_plan_prompt_new_format` ✅
- `test_plan_prompt_requires_job_index` ✅
- `test_track_backwards_compatibility` ✅
- `test_project_status_defaults` ✅
- `test_vocals_config_defaults` ✅

**Verify script checks**:
- ✅ Python syntax check (`compileall`)
- ✅ CLI smoke test (`python -m ytf --help`)
- ✅ Schema validation (Pydantic Project model)
- ✅ Unit tests (pytest)

## Screenshots/logs

N/A (all verification is CLI-based)

## Notes

- Verify script runs successfully without any API keys set
- All checks are offline (no network calls)
- pytest is installed via `requirements-dev.txt`
- CI workflow uses Python 3.11 and resilient dependency installation
- All changes are additive (no breaking changes to existing workflows)
