# Testing Guide

## Automated Tests

### Unit Tests
```bash
# Run all tests
make test

# Run with pytest directly
PYTHONPATH=src python -m pytest tests/ -v
```

### Verification Script
```bash
# Full offline verification
bash scripts/verify.sh
```

This runs:
1. Syntax check (`python -m compileall -q src`)
2. CLI smoke test (`python -m ytf --help`)
3. Schema validation (Pydantic model instantiation)
4. Unit tests (`pytest -q tests/`)

## Code Quality

### Format Code
```bash
make format
```

Runs black and ruff --fix on all source files.

### Lint Code
```bash
make lint
```

Runs ruff to check for issues without fixing.

### Check Formatting (CI)
```bash
make check-format
```

Runs black --check and ruff check (fails if formatting needed).

## Manual Testing

### Pipeline End-to-End

1. **Create project**:
   ```bash
   ytf new "Test Theme" --channel cafe_jazz --minutes 10 --tracks 2
   ```

2. **Run pipeline** (requires API keys):
   ```bash
   ytf run <project_id> --to render
   ```

3. **Verify outputs**:
   - `projects/<id>/output/final.mp4` exists
   - `projects/<id>/output/chapters.txt` exists
   - `projects/<id>/assets/thumbnail.png` exists

### CLI Smoke Tests

```bash
# Verify CLI loads
ytf --help

# Check doctor
ytf doctor

# Verify queue
ytf queue ls
```

### Provider Tests (Requires API Keys)

```bash
# Full doctor (with API checks)
make doctor

# Test Suno (costs money - use sparingly)
ytf new "API Test" --channel cafe_jazz --tracks 1
ytf run <project_id> --to generate
```

## Test Coverage

Current test files:
- `tests/test_project_schema.py` - Pydantic model validation

### What Tests Cover
- Minimal project creation
- All-fields populated projects
- Backward compatibility (field migrations)
- Default values and field constraints
- Vocals/Lyrics config validation

## Adding New Tests

1. Create test file in `tests/` following `test_*.py` pattern
2. Use pytest fixtures for common setup
3. Keep tests offline (no API keys required)
4. Run `make test` to verify

Example:
```python
def test_example_feature():
    """Test description."""
    # Arrange
    data = {...}

    # Act
    result = function_under_test(data)

    # Assert
    assert result == expected_value
```

## CI/CD

GitHub Actions workflow at `.github/workflows/ci.yml` runs:
- Python 3.11 setup
- Install dependencies
- Run `scripts/verify.sh`

### Running CI Locally
```bash
# Simulate CI environment
bash scripts/verify.sh
```

## Quick Verification

One-liner for quick checks:
```bash
make test && make lint && ytf --help
```
