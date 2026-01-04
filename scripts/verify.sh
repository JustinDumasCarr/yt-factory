#!/bin/sh
# Verification script for yt-factory
# Runs offline checks: syntax, CLI smoke, schema validation, unit tests
# Must not require API keys or network access.

set -e

echo "=========================================="
echo "VERIFICATION"
echo "=========================================="
echo ""

# Detect Python
PY=${PY:-python3}
if ! command -v "$PY" >/dev/null 2>&1; then
    echo "Error: python3 not found"
    exit 1
fi

# Set PYTHONPATH for src/ytf imports
export PYTHONPATH="${PYTHONPATH:+$PYTHONPATH:}$(pwd)/src"

# 1. Syntax check
echo "Checking Python syntax..."
"$PY" -m compileall -q src || {
    echo "Error: Syntax check failed"
    exit 1
}

# 2. CLI smoke test (no API keys required)
echo "Testing CLI (--help)..."
"$PY" -m ytf --help >/dev/null || {
    echo "Error: CLI --help failed"
    exit 1
}

# 3. Schema validation smoke test (Pydantic)
echo "Testing project.json schema validation..."
"$PY" -c "
from ytf.project import Project, ProjectStatus, VocalsConfig, LyricsConfig, VideoConfig, UploadConfig
from datetime import datetime

# Minimal valid project
data = {
    'project_id': 'test_20260104_000000_test',
    'created_at': datetime.now().isoformat(),
    'theme': 'test theme',
    'target_minutes': 60,
    'track_count': 25,
    'vocals': {'enabled': False},
    'lyrics': {'enabled': False},
    'video': {'width': 1920, 'height': 1080, 'fps': 30},
    'upload': {'privacy': 'unlisted'},
    'status': {'current_step': 'new'}
}

# Should not raise
project = Project(**data)
assert project.project_id == 'test_20260104_000000_test'
assert project.status.current_step == 'new'
print('Schema validation: OK')
" || {
    echo "Error: Schema validation failed"
    exit 1
}

# 4. Unit tests (if pytest available)
if "$PY" -m pytest --version >/dev/null 2>&1; then
    echo "Running unit tests..."
    "$PY" -m pytest -q tests/ || {
        echo "Error: Unit tests failed"
        exit 1
    }
else
    echo "Skipping unit tests (pytest not installed)"
    echo "  Install with: pip install -r requirements-dev.txt"
fi

echo ""
echo "=========================================="
echo "VERIFY PASSED"
echo "=========================================="
