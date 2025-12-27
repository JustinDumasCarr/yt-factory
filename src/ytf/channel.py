"""
Channel profile loader: reads YAML channel configs and validates with Pydantic.

Each channel profile defines defaults, constraints, templates, and upload settings.
"""

import yaml
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field


class DurationRules(BaseModel):
    """Duration and track count rules for a channel."""

    target_minutes: int = 60
    min_minutes: int = 30
    max_minutes: int = 480  # 8 hours for sleep
    track_count: int = 25
    min_track_seconds: int = 60  # Minimum track duration for QC


class PromptConstraints(BaseModel):
    """Prompt generation constraints."""

    default_instrumental: bool = True
    default_vocals: bool = False
    energy_level: str = "medium"  # low, medium, high
    banned_terms: list[str] = Field(default_factory=list)
    style_guidance: str = ""  # Additional guidance for Gemini


class TitleTemplate(BaseModel):
    """A title template variant."""

    template: str  # Can include {theme}, {track_count} placeholders
    example: str = ""  # Example output


class DescriptionTemplate(BaseModel):
    """Description template with CTA placeholder."""

    template: str  # Can include {theme}, {chapters}, {cta} placeholders
    cta_block: str  # CTA text block to insert


class CTATemplate(BaseModel):
    """CTA variant template."""

    variant_id: str
    short_text: str  # Short CTA text
    long_text: str  # Long CTA text


class TagRules(BaseModel):
    """Tag whitelist and banned terms."""

    whitelist: list[str] = Field(default_factory=list)  # Allowed tags (empty = no restriction)
    banned_terms: list[str] = Field(default_factory=list)  # Banned terms (policy risk)


class ThumbnailStyle(BaseModel):
    """Thumbnail style preset."""

    font_family: str = "Cinzel"
    layout_variant: str = "big_title_small_subtitle"  # big_title_small_subtitle, centered_title, bottom_title
    safe_words: list[str] = Field(default_factory=list)  # Words to avoid in thumbnails
    font_size_title: Optional[int] = None  # Override calculated font size for title (default: auto-calculated)
    font_size_subtitle: Optional[int] = None  # Override calculated font size for subtitle (default: auto-calculated)
    text_color: str = "0xF6F6F0"  # FFmpeg color format (0xRRGGBB), default: warm off-white
    text_position: Optional[str] = None  # Override position (default: based on layout_variant)
    background_overlay: Optional[str] = None  # Optional rgba overlay for text readability (e.g., "black@0.3")


class UploadDefaults(BaseModel):
    """Upload default settings."""

    privacy: str = "unlisted"  # public, private, unlisted
    category_id: str = "10"  # YouTube category ID (10 = Music)
    default_language: str = "en"
    made_for_kids: bool = False


class ChannelProfile(BaseModel):
    """Complete channel profile configuration."""

    channel_id: str
    name: str
    intent: str  # music_compilation, sleep, focus, etc.
    duration_rules: DurationRules = Field(default_factory=DurationRules)
    prompt_constraints: PromptConstraints = Field(default_factory=PromptConstraints)
    title_templates: list[TitleTemplate] = Field(default_factory=list)
    description_template: DescriptionTemplate
    cta_variants: list[CTATemplate] = Field(default_factory=list)
    tag_rules: TagRules = Field(default_factory=TagRules)
    thumbnail_style: ThumbnailStyle = Field(default_factory=ThumbnailStyle)
    upload_defaults: UploadDefaults = Field(default_factory=UploadDefaults)


# Channel configs directory (repo root)
CHANNELS_DIR = Path(__file__).parent.parent.parent / "channels"


def get_channel(channel_id: str) -> ChannelProfile:
    """
    Load and validate a channel profile by ID.

    Args:
        channel_id: Channel ID (filename without .yaml)

    Returns:
        Validated ChannelProfile

    Raises:
        FileNotFoundError: If channel config doesn't exist
        ValueError: If channel config is invalid
    """
    channel_path = CHANNELS_DIR / f"{channel_id}.yaml"

    if not channel_path.exists():
        raise FileNotFoundError(
            f"Channel config not found: {channel_id}. Expected {channel_path}"
        )

    try:
        with open(channel_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML in channel config: {e}") from e

    # Ensure channel_id matches filename
    if data.get("channel_id") != channel_id:
        data["channel_id"] = channel_id

    try:
        return ChannelProfile(**data)
    except Exception as e:
        raise ValueError(f"Invalid channel config structure: {e}") from e


def list_channels() -> list[str]:
    """
    List all available channel IDs.

    Returns:
        List of channel IDs (filenames without .yaml)
    """
    if not CHANNELS_DIR.exists():
        return []

    channels = []
    for path in CHANNELS_DIR.glob("*.yaml"):
        channel_id = path.stem
        channels.append(channel_id)

    return sorted(channels)

