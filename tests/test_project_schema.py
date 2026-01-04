"""
Offline unit tests for project.json schema validation.

These tests validate Pydantic models without requiring:
- API keys (Gemini, Suno, YouTube)
- Network access
- FFmpeg/FFprobe
- Existing project directories
"""

from datetime import datetime

import pytest

from ytf.project import (
    PlanPrompt,
    Project,
    ProjectStatus,
    Track,
    VocalsConfig,
)


def test_minimal_project_creation():
    """Test creating a minimal valid Project."""
    data = {
        "project_id": "test_20260104_000000_test",
        "created_at": datetime.now().isoformat(),
        "theme": "test theme",
        "target_minutes": 60,
        "track_count": 25,
    }

    project = Project(**data)

    assert project.project_id == "test_20260104_000000_test"
    assert project.theme == "test theme"
    assert project.target_minutes == 60
    assert project.track_count == 25
    assert project.status.current_step == "new"
    assert project.vocals.enabled is False
    assert project.lyrics.enabled is False
    assert project.video.width == 1920
    assert project.video.height == 1080
    assert project.video.fps == 30
    assert project.upload.privacy == "unlisted"


def test_project_with_all_fields():
    """Test creating a Project with all optional fields populated."""
    data = {
        "project_id": "test_full_20260104_000000",
        "created_at": datetime.now().isoformat(),
        "theme": "full test",
        "channel_id": "cafe_jazz",
        "intent": "test intent",
        "target_minutes": 120,
        "track_count": 50,
        "vocals": {"enabled": True},
        "lyrics": {"enabled": True, "source": "gemini"},
        "video": {"width": 1920, "height": 1080, "fps": 30},
        "upload": {
            "privacy": "public",
            "category_id": "10",
            "made_for_kids": False,
            "default_language": "en",
        },
        "status": {
            "current_step": "plan",
            "last_successful_step": "new",
            "attempts": {"plan": 1},
        },
    }

    project = Project(**data)

    assert project.channel_id == "cafe_jazz"
    assert project.vocals.enabled is True
    assert project.lyrics.enabled is True
    assert project.lyrics.source == "gemini"
    assert project.upload.privacy == "public"
    assert project.status.current_step == "plan"
    assert project.status.last_successful_step == "new"


def test_plan_prompt_backwards_compatibility():
    """Test PlanPrompt backwards compatibility: track_index -> job_index."""
    # Old format with track_index
    old_data = {
        "track_index": 0,
        "style": "Jazz",
        "title": "Test Track",
        "prompt": "A smooth jazz piece",
        "vocals_enabled": False,
    }

    prompt = PlanPrompt(**old_data)

    # Should have job_index set from track_index
    assert prompt.job_index == 0
    assert prompt.track_index == 0  # Still present for backwards compat
    assert prompt.style == "Jazz"
    assert prompt.title == "Test Track"


def test_plan_prompt_new_format():
    """Test PlanPrompt with new job_index format."""
    new_data = {
        "job_index": 5,
        "style": "Ambient",
        "title": "Ambient Track",
        "prompt": "A calming ambient piece",
        "vocals_enabled": False,
    }

    prompt = PlanPrompt(**new_data)

    assert prompt.job_index == 5
    assert prompt.style == "Ambient"
    assert prompt.title == "Ambient Track"


def test_plan_prompt_requires_job_index():
    """Test that PlanPrompt requires job_index (or track_index for backwards compat)."""
    # Missing both job_index and track_index should fail
    invalid_data = {
        "style": "Jazz",
        "title": "Test",
        "prompt": "A test",
    }

    with pytest.raises(ValueError, match="job_index is required"):
        PlanPrompt(**invalid_data)


def test_track_backwards_compatibility():
    """Test Track backwards compatibility: infer job_index from track_index."""
    track_data = {
        "track_index": 3,
        "prompt": "A test track",
        "provider": "suno",
        "status": "ok",
        "duration_seconds": 120.0,
    }

    track = Track(**track_data)

    # Should infer job_index from track_index
    assert track.track_index == 3
    assert track.job_index == 3
    assert track.variant_index == 0  # Default for old tracks


def test_project_status_defaults():
    """Test ProjectStatus defaults."""
    status = ProjectStatus()

    assert status.current_step == "new"
    assert status.last_successful_step is None
    assert status.last_error is None
    assert status.attempts == {}


def test_vocals_config_defaults():
    """Test VocalsConfig defaults."""
    vocals = VocalsConfig()

    assert vocals.enabled is False
