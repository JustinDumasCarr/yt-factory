"""
Soundbank management: global reusable audio stems for tinnitus channel.

The soundbank stores reusable audio stems (rain, crickets, ocean, etc.) that can be
looped and layered to create long-form tinnitus relief videos without calling Suno
for every project.
"""

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

# Soundbank directory (repo root)
SOUNDBANK_DIR = Path(__file__).parent.parent.parent / "assets" / "soundbank"
SOUNDBANK_JSON = SOUNDBANK_DIR / "soundbank.json"


class SoundbankEntry(BaseModel):
    """Metadata for a single sound in the soundbank."""

    sound_id: str  # Unique identifier (e.g., "rain_gentle_001")
    filename: str  # Audio file name (e.g., "rain_gentle_001.mp3")
    name: str  # Human-readable name (e.g., "Gentle Rain")
    description: Optional[str] = None  # Optional description
    duration_seconds: float  # Duration of the audio file
    created_at: str  # ISO timestamp
    source: str = "suno"  # "suno" | "manual" | "freesound" | "pixabay"
    license_type: Optional[str] = None  # "CC0" | "CC-BY" | "Pixabay" | "Suno" | "manual" | "custom"
    license_url: Optional[str] = None  # URL to license text/documentation
    commercial_ok: bool = False  # Whether sound can be used commercially (default False for safety)


class Soundbank(BaseModel):
    """Soundbank metadata container."""

    sounds: list[SoundbankEntry] = Field(default_factory=list)
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())


def _ensure_soundbank_dir() -> None:
    """Ensure soundbank directory exists."""
    SOUNDBANK_DIR.mkdir(parents=True, exist_ok=True)


def _load_soundbank() -> Soundbank:
    """Load soundbank.json or return empty soundbank."""
    _ensure_soundbank_dir()
    
    if not SOUNDBANK_JSON.exists():
        return Soundbank()
    
    try:
        with open(SOUNDBANK_JSON, "r", encoding="utf-8") as f:
            data = json.load(f)
        return Soundbank(**data)
    except Exception:
        # If corrupted, return empty soundbank
        return Soundbank()


def _save_soundbank(soundbank: Soundbank) -> None:
    """Save soundbank.json."""
    _ensure_soundbank_dir()
    
    soundbank.updated_at = datetime.now().isoformat()
    with open(SOUNDBANK_JSON, "w", encoding="utf-8") as f:
        json.dump(soundbank.model_dump(), f, indent=2, ensure_ascii=False)


def list_sounds() -> list[SoundbankEntry]:
    """
    List all sounds in the soundbank.
    
    Returns:
        List of soundbank entries
    """
    soundbank = _load_soundbank()
    return soundbank.sounds


def get_sound(sound_id: str) -> Optional[SoundbankEntry]:
    """
    Get a specific sound by ID.
    
    Args:
        sound_id: Sound ID to look up
        
    Returns:
        SoundbankEntry if found, None otherwise
    """
    soundbank = _load_soundbank()
    for sound in soundbank.sounds:
        if sound.sound_id == sound_id:
            return sound
    return None


def get_sound_path(sound_id: str) -> Optional[Path]:
    """
    Get the file path for a sound.
    
    Args:
        sound_id: Sound ID
        
    Returns:
        Path to audio file if exists, None otherwise
    """
    sound = get_sound(sound_id)
    if not sound:
        return None
    
    path = SOUNDBANK_DIR / sound.filename
    if path.exists():
        return path
    return None


def add_sound_from_file(
    file_path: str,
    sound_id: str,
    name: str,
    description: Optional[str] = None,
    source: str = "manual",
) -> SoundbankEntry:
    """
    Add an existing audio file to the soundbank.
    
    Args:
        file_path: Path to audio file to add
        sound_id: Unique identifier for the sound
        name: Human-readable name
        description: Optional description
        source: "manual" or "suno"
        
    Returns:
        Created SoundbankEntry
        
    Raises:
        FileNotFoundError: If source file doesn't exist
        ValueError: If sound_id already exists
        RuntimeError: If duration cannot be determined
    """
    from ytf.utils.ffprobe import get_duration_seconds
    
    source_path = Path(file_path)
    if not source_path.exists():
        raise FileNotFoundError(f"Source file not found: {file_path}")
    
    # Check if sound_id already exists
    soundbank = _load_soundbank()
    if any(s.sound_id == sound_id for s in soundbank.sounds):
        raise ValueError(f"Sound ID already exists: {sound_id}")
    
    # Get duration
    try:
        duration = get_duration_seconds(source_path)
    except Exception as e:
        raise RuntimeError(f"Failed to get duration: {e}") from e
    
    # Determine file extension
    ext = source_path.suffix.lower()
    if ext not in (".mp3", ".wav", ".m4a", ".ogg"):
        raise ValueError(f"Unsupported audio format: {ext}")
    
    # Copy file to soundbank
    _ensure_soundbank_dir()
    filename = f"{sound_id}{ext}"
    dest_path = SOUNDBANK_DIR / filename
    shutil.copy2(source_path, dest_path)
    
    # Set license defaults based on source
    license_type = None
    commercial_ok = False
    if source == "manual":
        license_type = "manual"
        commercial_ok = True  # User-provided, assume they have rights
    elif source == "suno":
        license_type = "Suno"
        commercial_ok = True  # Suno allows commercial use per their terms
    
    # Create entry
    entry = SoundbankEntry(
        sound_id=sound_id,
        filename=filename,
        name=name,
        description=description,
        duration_seconds=duration,
        created_at=datetime.now().isoformat(),
        source=source,
        license_type=license_type,
        commercial_ok=commercial_ok,
    )
    
    # Add to soundbank
    soundbank.sounds.append(entry)
    _save_soundbank(soundbank)
    
    return entry


def search_freesound(query: str, limit: int = 10) -> list[dict]:
    """
    Search for sounds on Freesound.
    
    Args:
        query: Search query (keywords, tags, etc.)
        limit: Maximum number of results to return
        
    Returns:
        List of sound result dicts with keys: id, name, license, url, etc.
        
    Raises:
        RuntimeError: If API call fails or API key not set
    """
    try:
        from ytf.providers.freesound import FreesoundProvider
        
        with FreesoundProvider() as provider:
            return provider.search(query, limit=limit, filter_license=True)
    except ValueError as e:
        # API key not set - return empty list
        return []
    except Exception as e:
        raise RuntimeError(f"Freesound search failed: {e}") from e


def search_pixabay(query: str, limit: int = 10) -> list[dict]:
    """
    Search for audio files on Pixabay.
    
    Args:
        query: Search query (keywords)
        limit: Maximum number of results to return
        
    Returns:
        List of audio result dicts with keys: id, title, license, download_url, etc.
        
    Raises:
        RuntimeError: If API call fails or API key not set
    """
    try:
        from ytf.providers.pixabay import PixabayProvider
        
        with PixabayProvider() as provider:
            return provider.search(query, limit=limit)
    except ValueError as e:
        # API key not set - return empty list
        return []
    except Exception as e:
        raise RuntimeError(f"Pixabay search failed: {e}") from e


def download_from_freesound(sound_id: int, output_path: Path) -> dict:
    """
    Download a sound from Freesound and return metadata.
    
    Args:
        sound_id: Freesound sound ID
        output_path: Path to save the audio file
        
    Returns:
        Dict with sound metadata including license info
        
    Raises:
        RuntimeError: If download fails
        FileNotFoundError: If sound doesn't exist
    """
    from ytf.providers.freesound import FreesoundProvider
    
    with FreesoundProvider() as provider:
        return provider.download(sound_id, str(output_path))


def download_from_pixabay(download_url: str, output_path: Path) -> dict:
    """
    Download an audio file from Pixabay using a download URL.
    
    Args:
        download_url: Direct download URL from search results
        output_path: Path to save the audio file
        
    Returns:
        Dict with audio metadata
        
    Raises:
        RuntimeError: If download fails
    """
    from ytf.providers.pixabay import PixabayProvider
    
    with PixabayProvider() as provider:
        return provider.download_with_url(download_url, str(output_path))


def _generate_via_suno(
    sound_id: str,
    name: str,
    style: str,
    prompt: str,
    description: Optional[str] = None,
) -> SoundbankEntry:
    """
    Generate a new sound using Suno API and add it to soundbank.
    
    Args:
        sound_id: Unique identifier for the sound
        name: Human-readable name
        style: Music style/genre for Suno (use "Ambient", "Nature Sounds", "White Noise" for ambient)
        prompt: Audio description/prompt for Suno (used in title/context even if instrumental=True)
        description: Optional description
        
    Returns:
        Created SoundbankEntry
        
    Raises:
        ValueError: If sound_id already exists or Suno generation fails
        RuntimeError: If download or processing fails
    """
    from ytf.providers.suno import SunoProvider
    from ytf.utils.ffprobe import get_duration_seconds
    
    # Check if sound_id already exists
    soundbank = _load_soundbank()
    if any(s.sound_id == sound_id for s in soundbank.sounds):
        raise ValueError(f"Sound ID already exists: {sound_id}")
    
    # Initialize Suno provider
    provider = SunoProvider()
    
    try:
        # For ambient sounds, use negativeTags to exclude musical elements
        # When instrumental=True, Suno ignores prompt but uses style and title
        # Use negativeTags to guide away from song-like elements
        negative_tags = "Song, Melody, Beat, Drums, Rhythm, Music, Composition, Tune, Harmony, Chord"
        
        # Ensure style is ambient-focused if not already
        ambient_styles = ["Ambient", "Nature Sounds", "White Noise", "Soundscape", "Field Recording"]
        if style not in ambient_styles:
            # Prefer "Ambient" as default for ambient sounds
            style = "Ambient"
        
        # Make title more descriptive to guide generation
        # Include the prompt description in the title since prompt is ignored
        enhanced_title = f"{name} - {prompt}"[:80]  # Suno title max is 80 chars
        
        # Generate music (instrumental for ambient sounds)
        task_id = provider.generate_music(
            style=style,
            title=enhanced_title,
            prompt=prompt,  # Still pass for API completeness, even though ignored when instrumental=True
            instrumental=True,  # Tinnitus sounds are instrumental
            negative_tags=negative_tags,  # Exclude musical elements
        )
        
        # Poll until complete
        status_info = provider.poll_until_complete(task_id, max_wait_minutes=20)
        
        if status_info["status"] != "complete":
            error = status_info.get("error", "Unknown error")
            raise RuntimeError(f"Suno generation failed: {error}")
        
        # Get first track from results
        suno_data = status_info.get("sunoData", [])
        if not suno_data or len(suno_data) == 0:
            raise RuntimeError("Suno returned no audio data")
        
        # Use first variant (index 0)
        track_data = suno_data[0]
        audio_url = track_data.get("audioUrl") or track_data.get("streamAudioUrl")
        
        if not audio_url:
            raise RuntimeError("Suno track has no audio URL")
        
        # Download audio
        _ensure_soundbank_dir()
        filename = f"{sound_id}.mp3"
        temp_path = SOUNDBANK_DIR / f"{sound_id}_temp.mp3"
        
        provider.download_audio(audio_url, str(temp_path))
        
        # Get duration
        duration = get_duration_seconds(temp_path)
        
        # Rename to final filename
        final_path = SOUNDBANK_DIR / filename
        temp_path.rename(final_path)
        
        # Create entry with Suno license
        entry = SoundbankEntry(
            sound_id=sound_id,
            filename=filename,
            name=name,
            description=description,
            duration_seconds=duration,
            created_at=datetime.now().isoformat(),
            source="suno",
            license_type="Suno",
            commercial_ok=True,  # Suno allows commercial use per their terms
        )
        
        # Add to soundbank
        soundbank.sounds.append(entry)
        _save_soundbank(soundbank)
        
        return entry
        
    finally:
        provider.close()


def generate_sound(
    sound_id: str,
    name: str,
    query: str,
    style: Optional[str] = None,
    description: Optional[str] = None,
    source: str = "auto",
) -> SoundbankEntry:
    """
    Generate or download a sound from multiple sources with automatic fallback.
    
    Priority order: Freesound → Pixabay → Suno
    
    Args:
        sound_id: Unique identifier for the sound
        name: Human-readable name
        query: Search query (used for Freesound/Pixabay) or prompt (for Suno)
        style: Music style for Suno (default: "Ambient")
        description: Optional description
        source: Source to use ("freesound", "pixabay", "suno", or "auto" for fallback)
        
    Returns:
        Created SoundbankEntry
        
    Raises:
        ValueError: If sound_id already exists
        RuntimeError: If all sources fail
    """
    from ytf.utils.ffprobe import get_duration_seconds
    
    # Check if sound_id already exists
    soundbank = _load_soundbank()
    if any(s.sound_id == sound_id for s in soundbank.sounds):
        raise ValueError(f"Sound ID already exists: {sound_id}")
    
    _ensure_soundbank_dir()
    filename = f"{sound_id}.mp3"
    output_path = SOUNDBANK_DIR / filename
    
    # Try sources in priority order
    sources_to_try = []
    if source == "auto":
        sources_to_try = ["freesound", "pixabay", "suno"]
    elif source in ["freesound", "pixabay", "suno"]:
        sources_to_try = [source]
    else:
        raise ValueError(f"Invalid source: {source}. Must be 'freesound', 'pixabay', 'suno', or 'auto'")
    
    last_error = None
    
    for source_name in sources_to_try:
        try:
            if source_name == "freesound":
                # Search Freesound
                results = search_freesound(query, limit=1)
                if not results:
                    raise RuntimeError("No Freesound results found")
                
                # Download first result
                freesound_id = results[0]["id"]
                metadata = download_from_freesound(freesound_id, output_path)
                
                # Get duration
                duration = get_duration_seconds(output_path)
                
                # Create entry
                entry = SoundbankEntry(
                    sound_id=sound_id,
                    filename=filename,
                    name=name or metadata.get("name", f"Freesound {freesound_id}"),
                    description=description or metadata.get("description", ""),
                    duration_seconds=duration,
                    created_at=datetime.now().isoformat(),
                    source="freesound",
                    license_type=metadata.get("license"),
                    license_url=metadata.get("license_url"),
                    commercial_ok=True,  # CC0 and CC-BY allow commercial use
                )
                
                soundbank.sounds.append(entry)
                _save_soundbank(soundbank)
                return entry
                
            elif source_name == "pixabay":
                # Search Pixabay
                results = search_pixabay(query, limit=1)
                if not results:
                    raise RuntimeError("No Pixabay results found")
                
                # Download first result
                download_url = results[0].get("download_url")
                if not download_url:
                    raise RuntimeError("Pixabay result missing download URL")
                
                metadata = download_from_pixabay(download_url, output_path)
                
                # Get duration
                duration = get_duration_seconds(output_path)
                
                # Create entry
                entry = SoundbankEntry(
                    sound_id=sound_id,
                    filename=filename,
                    name=name or results[0].get("name", results[0].get("title", "")),
                    description=description or "",
                    duration_seconds=duration,
                    created_at=datetime.now().isoformat(),
                    source="pixabay",
                    license_type="Pixabay",
                    license_url=metadata.get("license_url", "https://pixabay.com/service/license/"),
                    commercial_ok=True,  # Pixabay allows commercial use
                )
                
                soundbank.sounds.append(entry)
                _save_soundbank(soundbank)
                return entry
                
            elif source_name == "suno":
                # Generate via Suno
                return _generate_via_suno(
                    sound_id=sound_id,
                    name=name,
                    style=style or "Ambient",
                    prompt=query,
                    description=description,
                )
                
        except (ValueError, RuntimeError, FileNotFoundError) as e:
            # API key not set or source failed - try next source
            last_error = e
            continue
        except Exception as e:
            # Unexpected error - try next source
            last_error = e
            continue
    
    # All sources failed
    raise RuntimeError(
        f"All sound sources failed. Last error: {last_error}"
    ) from last_error


# Keep generate_sound_via_suno as a convenience wrapper for backwards compatibility
def generate_sound_via_suno(
    sound_id: str,
    name: str,
    style: str,
    prompt: str,
    description: Optional[str] = None,
) -> SoundbankEntry:
    """
    Generate a new sound using Suno API and add it to soundbank.
    
    This is a convenience wrapper around _generate_via_suno() for backwards compatibility.
    
    Args:
        sound_id: Unique identifier for the sound
        name: Human-readable name
        style: Music style/genre for Suno
        prompt: Audio description/prompt for Suno
        description: Optional description
        
    Returns:
        Created SoundbankEntry
    """
    return _generate_via_suno(sound_id, name, style, prompt, description)
