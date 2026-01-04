# Tests

## Test cases

### Test 1: Verify script runs offline
- **Given**: No API keys set (GEMINI_API_KEY, SUNO_API_KEY, YOUTUBE_OAUTH_CREDENTIALS_PATH unset)
- **When**: Run `bash scripts/verify.sh`
- **Then**: Script exits 0 with "VERIFY PASSED" message

### Test 2: Schema validation works
- **Given**: Pydantic models in `src/ytf/project.py`
- **When**: Run verify script (includes embedded schema validation)
- **Then**: Schema validation passes (creates minimal Project instance)

### Test 3: Unit tests pass
- **Given**: `tests/test_project_schema.py` with 8 test cases
- **When**: Run `pytest tests/`
- **Then**: All 8 tests pass (minimal project, full project, backwards compat, etc.)

### Test 4: Makefile test target is offline
- **Given**: `Makefile` updated
- **When**: Run `make test`
- **Then**: Calls `scripts/verify.sh` (no `ytf doctor` call)

### Test 5: Doctor offline works
- **Given**: `make doctor-offline` target exists
- **When**: Run `make doctor-offline`
- **Then**: Checks Python version, FFmpeg/FFprobe presence, writable projects dir (no API key checks)

## Test coverage

- [x] Unit tests (`tests/test_project_schema.py` - 8 tests)
- [ ] Integration tests (N/A for this adoption)
- [ ] E2E tests (N/A for this adoption)
- [x] Manual test cases (verify script, make targets)

## Test results

All tests pass. See `evidence.md` for full verify output.
