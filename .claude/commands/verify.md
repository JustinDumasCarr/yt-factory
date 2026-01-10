# Verify

Run verification checks for yt-factory.

## When to Use
- Before committing changes
- After making code changes
- At session start to confirm project state

## Instructions

### Step 1: Run Offline Verification

```bash
make test
```

This runs:
- Syntax check (`python -m compileall -q src`)
- CLI smoke test (`python -m ytf --help`)
- Schema validation (Pydantic model instantiation)
- Unit tests (`pytest -q tests/`)

### Step 2: Run Code Quality Checks

```bash
make lint
```

This runs ruff to check for linting errors.

### Step 3: Run CLI Smoke Test

```bash
PYTHONPATH=src python -m ytf --help
```

Verify the CLI loads and displays help correctly.

### Step 4: Run Offline Doctor

```bash
make doctor-offline
```

Checks:
- Python version
- FFmpeg availability
- FFprobe availability
- Projects directory writable

### Step 5 (Optional): Run Full Doctor

Only if API keys are configured:

```bash
make doctor
```

Checks all prerequisites including API key validity.

## Expected Output

All checks should pass:
- Tests: All green
- Lint: No errors
- CLI: Help displays correctly
- Doctor: All checks green

## If Verification Fails

1. Read error messages carefully
2. Fix the issue
3. Re-run verification
4. If stuck after 2 attempts, notify the user

## Quick One-Liner

```bash
make test && make lint && ytf --help
```
