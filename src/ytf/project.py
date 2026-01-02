"""
Project state management: read/write project.json, validation, folder creation.

This module provides the single source of truth for project state.
All project data is stored in project.json following the schema in docs/03_PROJECT_SCHEMA.md.
"""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator


# Step enum values
StepType = str  # "new" | "plan" | "generate" | "review" | "render" | "upload" | "done"
PrivacyType = str  # "unlisted" | "private" | "public"
LyricsSourceType = str  # "gemini" | "manual"
TrackStatusType = str  # "ok" | "failed"


class LastError(BaseModel):
    """Error information persisted to project.json."""

    step: str
    message: str
    stack: str
    at: str  # ISO timestamp
    kind: Optional[str] = None  # Error category: auth, rate_limit, timeout, provider_http, validation, ffmpeg, unknown
    provider: Optional[str] = None  # Provider name: gemini, suno, youtube
    raw: Optional[str] = None  # Raw error details (truncated if huge)


class ProjectStatus(BaseModel):
    """Current status of the project."""

    current_step: StepType = "new"
    last_successful_step: Optional[StepType] = None
    last_error: Optional[LastError] = None
    attempts: dict[str, int] = Field(default_factory=dict)  # Step -> attempt count


class VocalsConfig(BaseModel):
    """Vocals configuration."""

    enabled: bool = False


class LyricsConfig(BaseModel):
    """Lyrics configuration."""

    enabled: bool = False
    source: LyricsSourceType = "gemini"


class VideoConfig(BaseModel):
    """Video output settings."""

    width: int = 1920
    height: int = 1080
    fps: int = 30


class UploadConfig(BaseModel):
    """Upload settings."""

    privacy: PrivacyType = "unlisted"
    category_id: str = "10"  # YouTube category ID (10 = Music)
    made_for_kids: bool = False
    default_language: str = "en"


class FunnelConfig(BaseModel):
    """Funnel/CTA configuration for app signups."""

    landing_url: Optional[str] = None
    utm_source: Optional[str] = None
    utm_campaign: Optional[str] = None
    cta_variant_id: Optional[str] = None


class SoundbankRef(BaseModel):
    """Reference to a sound in the global soundbank."""

    sound_id: str  # Unique identifier for the sound (e.g., "rain_gentle_001")
    volume: float = 1.0  # Volume multiplier (0.0 to 1.0, default 1.0)


class TinnitusMixRecipe(BaseModel):
    """Mix recipe for tinnitus channel projects (uses soundbank stems, not Suno tracks)."""

    stems: list[SoundbankRef] = Field(default_factory=list)  # List of soundbank stems to mix
    mix_type: str = "layered"  # "single" (loop one stem) or "layered" (mix multiple stems)
    target_duration_seconds: float = 0.0  # Target duration in seconds (from target_minutes)


class QCIssue(BaseModel):
    """A single QC issue found on a track."""

    code: str  # e.g., "too_short", "leading_silence", "missing_file"
    message: str
    value: Optional[float] = None  # Optional measured value (e.g., duration, silence seconds)


class TrackQC(BaseModel):
    """Quality control data for a track."""

    passed: bool = False
    issues: list[QCIssue] = Field(default_factory=list)
    measured: dict[str, float] = Field(default_factory=dict)  # duration_seconds, leading_silence_seconds, etc.


class ReviewData(BaseModel):
    """Review/QC output data."""

    qc_report_json_path: Optional[str] = None
    qc_report_txt_path: Optional[str] = None
    approved_track_indices: list[int] = Field(default_factory=list)
    rejected_track_indices: list[int] = Field(default_factory=list)
    qc_summary: dict[str, int] = Field(default_factory=dict)  # passed_count, failed_count, etc.


class PlanPrompt(BaseModel):
    """A single prompt for Suno generation job (produces 2 variants)."""

    job_index: Optional[int] = None  # Job index (0-based). Each job produces 2 variants.
    style: str  # Music style/genre (required for Suno customMode)
    title: str  # Base track title (required for Suno customMode). Variants will be "Title I" and "Title II".
    prompt: str  # Musical description with mood, instrumentation, tempo
    seed_hint: Optional[str] = None
    vocals_enabled: bool = False
    lyrics_text: Optional[str] = None  # Lyrics text (used as prompt in Suno when instrumental=false)
    
    # Backwards compatibility: allow track_index for older project.json files
    track_index: Optional[int] = None  # Deprecated: use job_index instead
    
    @model_validator(mode='before')
    @classmethod
    def handle_backwards_compatibility(cls, data):
        """Convert old track_index to job_index for backwards compatibility."""
        if isinstance(data, dict):
            # If job_index is missing but track_index exists, convert it
            if 'job_index' not in data and 'track_index' in data:
                # Old behavior: each track_index was a separate job
                # New behavior: each job_index produces 2 variants
                # So job_index = track_index (1:1 mapping for old projects)
                data['job_index'] = data['track_index']
        return data
    
    @model_validator(mode='after')
    def validate_job_index(self):
        """Ensure job_index is set."""
        if self.job_index is None:
            raise ValueError("job_index is required (or track_index for backwards compatibility)")
        return self


class YouTubeMetadata(BaseModel):
    """YouTube video metadata."""

    title: str
    description: str
    tags: list[str] = Field(default_factory=list)


class PlanData(BaseModel):
    """Planning output data."""

    prompts: list[PlanPrompt] = Field(default_factory=list)
    youtube_metadata: Optional[YouTubeMetadata] = None


class TrackError(BaseModel):
    """Error information for a failed track."""

    message: str
    raw: Optional[str] = None
    attempt_count: int = 0  # Number of attempts made for this track


class Track(BaseModel):
    """Generated track metadata (one per variant)."""

    track_index: int  # Final track index (0-based, sequential across all variants)
    title: Optional[str] = None  # Track title (e.g., "Whispering Scrolls I" or "Whispering Scrolls II")
    style: Optional[str] = None  # Music style/genre
    prompt: str  # Musical description
    provider: str = "suno"
    job_id: Optional[str] = None  # Suno job ID (shared across both variants from same job)
    job_index: Optional[int] = None  # Which planned job this came from (0-based)
    variant_index: Optional[int] = None  # Which variant (0 or 1) from the job
    audio_url: Optional[str] = None  # Last known audio URL for resume
    audio_path: Optional[str] = None
    duration_seconds: float = 0.0
    status: TrackStatusType = "ok"
    error: Optional[TrackError] = None
    qc: Optional[TrackQC] = None
    
    @model_validator(mode='after')
    def fill_missing_fields_from_plan(self):
        """Fill missing title/style/job_index/variant_index for backwards compatibility."""
        # For old projects without these fields, infer from track_index
        # Old behavior: each track_index was a separate job, so job_index = track_index, variant_index = 0
        if self.job_index is None:
            self.job_index = self.track_index
        if self.variant_index is None:
            self.variant_index = 0
        # Title and style will be filled from plan prompts if available during render
        return self


class RenderData(BaseModel):
    """Render output data."""

    background_path: Optional[str] = None
    thumbnail_path: Optional[str] = None
    selected_track_indices: list[int] = Field(default_factory=list)
    output_mp4_path: Optional[str] = None
    chapters_path: Optional[str] = None
    description_path: Optional[str] = None


class YouTubeData(BaseModel):
    """YouTube upload result data."""

    video_id: Optional[str] = None
    uploaded_at: Optional[str] = None
    privacy: Optional[PrivacyType] = None
    title: Optional[str] = None
    thumbnail_uploaded: bool = False
    thumbnail_path: Optional[str] = None


class Project(BaseModel):
    """Root project model - single source of truth."""

    project_id: str
    created_at: str  # ISO timestamp
    theme: str
    channel_id: Optional[str] = None
    intent: Optional[str] = None
    target_minutes: int = 60
    track_count: int = 25
    vocals: VocalsConfig = Field(default_factory=VocalsConfig)
    lyrics: LyricsConfig = Field(default_factory=LyricsConfig)
    video: VideoConfig = Field(default_factory=VideoConfig)
    upload: UploadConfig = Field(default_factory=UploadConfig)
    status: ProjectStatus = Field(default_factory=ProjectStatus)
    funnel: FunnelConfig = Field(default_factory=FunnelConfig)
    plan: Optional[PlanData] = None
    tracks: list[Track] = Field(default_factory=list)
    tinnitus_recipe: Optional[TinnitusMixRecipe] = None  # For tinnitus channel: mix recipe using soundbank stems
    review: Optional[ReviewData] = None
    render: Optional[RenderData] = None
    youtube: Optional[YouTubeData] = None


# Project directory structure
PROJECTS_DIR = Path(__file__).parent.parent.parent / "projects"


def generate_project_id(theme: str) -> str:
    """
    Generate a project ID in format: YYYYMMDD_HHMMSS_<slug>.

    Args:
        theme: Project theme string

    Returns:
        Project ID string
    """
    now = datetime.now()
    timestamp = now.strftime("%Y%m%d_%H%M%S")

    # Create slug: lowercase, spaces to hyphens, remove non-alphanumeric except hyphens
    slug = theme.lower()
    slug = re.sub(r"[^\w\s-]", "", slug)  # Remove special chars
    slug = re.sub(r"[-\s]+", "-", slug)  # Collapse spaces/hyphens
    slug = slug.strip("-")  # Remove leading/trailing hyphens

    # Fallback if slug is empty
    if not slug:
        slug = "project"

    return f"{timestamp}_{slug}"


def create_project_folder(project_id: str) -> Path:
    """
    Create project folder structure with required subdirectories.

    Args:
        project_id: Project ID

    Returns:
        Path to project directory
    """
    project_dir = PROJECTS_DIR / project_id

    # Create main directory
    project_dir.mkdir(parents=True, exist_ok=True)

    # Create subdirectories
    (project_dir / "tracks").mkdir(exist_ok=True)
    (project_dir / "assets").mkdir(exist_ok=True)
    (project_dir / "output").mkdir(exist_ok=True)
    (project_dir / "logs").mkdir(exist_ok=True)

    return project_dir


def load_project(project_id: str) -> Project:
    """
    Load and validate project.json.

    Args:
        project_id: Project ID

    Returns:
        Validated Project model

    Raises:
        FileNotFoundError: If project.json doesn't exist
        ValueError: If project.json is invalid
    """
    project_dir = PROJECTS_DIR / project_id
    project_json_path = project_dir / "project.json"

    if not project_json_path.exists():
        raise FileNotFoundError(
            f"Project not found: {project_id}. Expected {project_json_path}"
        )

    try:
        with open(project_json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in project.json: {e}") from e

    try:
        return Project(**data)
    except Exception as e:
        raise ValueError(f"Invalid project.json structure: {e}") from e


def save_project(project: Project) -> None:
    """
    Save project to project.json with validation.

    Args:
        project: Project model to save

    Raises:
        ValueError: If project validation fails
    """
    project_dir = PROJECTS_DIR / project.project_id
    project_json_path = project_dir / "project.json"

    # Ensure directory exists
    project_dir.mkdir(parents=True, exist_ok=True)

    # Validate before saving
    try:
        # Pydantic will validate on model creation, but we can also call model_dump
        data = project.model_dump(mode="json", exclude_none=False)
    except Exception as e:
        raise ValueError(f"Project validation failed: {e}") from e

    # Write JSON with indentation
    with open(project_json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    # Add trailing newline
    with open(project_json_path, "a", encoding="utf-8") as f:
        f.write("\n")


def _classify_error(error: Exception) -> tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Classify error to extract kind, provider, and raw details.

    Args:
        error: Exception to classify

    Returns:
        Tuple of (kind, provider, raw) where:
        - kind: Error category (auth, rate_limit, timeout, provider_http, validation, ffmpeg, unknown)
        - provider: Provider name (gemini, suno, youtube) or None
        - raw: Raw error details (truncated) or None
    """
    kind = None
    provider = None
    raw = None

    error_str = str(error).lower()
    error_msg = str(error)

    # Detect provider from error message or exception type
    if "gemini" in error_str or "google.genai" in error_str or "genai" in error_str or "google.api_core" in error_str:
        provider = "gemini"
    elif "suno" in error_str or "sunoapi" in error_str or "api.sunoapi.org" in error_str:
        provider = "suno"
    elif "youtube" in error_str or "googleapiclient" in error_str or "youtube.upload" in error_str:
        provider = "youtube"
    elif "ffmpeg" in error_str or "ffprobe" in error_str:
        provider = None  # FFmpeg is not a provider, but we'll mark kind as ffmpeg

    # Classify error kind
    if "401" in error_msg or "403" in error_msg or "unauthorized" in error_str or "forbidden" in error_str or "authentication" in error_str:
        kind = "auth"
    elif "429" in error_msg or "rate limit" in error_str or "quota exceeded" in error_str or "too many requests" in error_str:
        kind = "rate_limit"
    elif "timeout" in error_str or "timed out" in error_str:
        kind = "timeout"
    elif "ffmpeg" in error_str or "ffprobe" in error_str:
        kind = "ffmpeg"
    elif "validation" in error_str or "invalid" in error_str or "valueerror" in error_str.lower():
        kind = "validation"
    elif hasattr(error, "status_code") or hasattr(error, "resp") or "http" in error_str:
        kind = "provider_http"
    else:
        kind = "unknown"

    # Extract raw error details
    raw_parts = []
    
    # Try to get HTTP response content (httpx)
    if hasattr(error, "response") and hasattr(error.response, "text"):
        status = getattr(error.response, "status_code", "?")
        raw_parts.append(f"HTTP {status}: {error.response.text[:500]}")
    # Try to get HTTP response content (googleapiclient)
    elif hasattr(error, "resp") and hasattr(error.resp, "status"):
        content = getattr(error, "content", None)
        if content:
            raw_parts.append(f"HTTP {error.resp.status}: {str(content)[:500]}")
        else:
            raw_parts.append(f"HTTP {error.resp.status}")
    
    # Try to get status code directly
    if hasattr(error, "status_code") and not any("HTTP" in p for p in raw_parts):
        raw_parts.append(f"Status: {error.status_code}")
    
    # Include full error message (truncated)
    if error_msg:
        raw_parts.append(error_msg[:1000])
    
    raw = " | ".join(raw_parts) if raw_parts else None
    if raw and len(raw) > 2000:
        raw = raw[:2000] + "... (truncated)"

    return kind, provider, raw


def update_status(
    project: Project, step: str, error: Optional[Exception] = None
) -> None:
    """
    Update project status and persist last_error if present.

    Args:
        project: Project to update
        step: Current step name
        error: Exception if step failed, None on success
    """
    import traceback

    project.status.current_step = step

    if error is None:
        # Success: update last_successful_step
        project.status.last_successful_step = step
        project.status.last_error = None
    else:
        # Classify error
        kind, provider, raw = _classify_error(error)
        
        # Failure: persist error details
        project.status.last_error = LastError(
            step=step,
            message=str(error),
            stack=traceback.format_exc(),
            at=datetime.now().isoformat(),
            kind=kind,
            provider=provider,
            raw=raw,
        )

