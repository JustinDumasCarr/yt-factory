"""
FFmpeg utilities for audio/video processing.

Provides functions for concatenating audio, normalizing loudness, and creating video files.
"""

import subprocess
import tempfile
from pathlib import Path
from typing import Optional, Union


def check_ffmpeg() -> bool:
    """
    Check if FFmpeg is available.

    Returns:
        True if FFmpeg is available, False otherwise
    """
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def generate_default_background(output_path: Union[str, Path], width: int = 1920, height: int = 1080) -> None:
    """
    Generate a default solid color background image using FFmpeg.

    Args:
        output_path: Path where to save the background image
        width: Image width in pixels (default 1920)
        height: Image height in pixels (default 1080)

    Raises:
        RuntimeError: If FFmpeg fails to generate the image
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        result = subprocess.run(
            [
                "ffmpeg",
                "-f", "lavfi",
                "-i", f"color=c=black:s={width}x{height}:d=1",
                "-frames:v", "1",
                "-y",  # Overwrite if exists
                str(output_path),
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode != 0:
            raise RuntimeError(
                f"FFmpeg failed to generate background: {result.stderr or result.stdout}"
            )

        if not output_path.exists():
            raise RuntimeError(f"Background image was not created at {output_path}")

    except subprocess.TimeoutExpired:
        raise RuntimeError("FFmpeg timed out while generating background") from None
    except Exception as e:
        raise RuntimeError(f"FFmpeg error generating background: {e}") from e


def concatenate_audio_files(
    audio_files: list[Union[str, Path]], output_path: Union[str, Path]
) -> None:
    """
    Concatenate multiple audio files using FFmpeg concat demuxer.

    Args:
        audio_files: List of paths to audio files to concatenate
        output_path: Path where to save the concatenated audio

    Raises:
        RuntimeError: If FFmpeg fails to concatenate files
        FileNotFoundError: If any input file doesn't exist
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Validate all input files exist
    for audio_file in audio_files:
        audio_path = Path(audio_file)
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

    # Create temporary file list for concat demuxer
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        concat_list_path = Path(f.name)
        for audio_file in audio_files:
            # Use absolute paths and escape single quotes
            abs_path = Path(audio_file).resolve()
            f.write(f"file '{abs_path}'\n")

    try:
        result = subprocess.run(
            [
                "ffmpeg",
                "-f", "concat",
                "-safe", "0",
                "-i", str(concat_list_path),
                "-c", "copy",
                "-y",  # Overwrite if exists
                str(output_path),
            ],
            capture_output=True,
            text=True,
            timeout=600,  # 10 minutes max for concatenation
        )

        if result.returncode != 0:
            raise RuntimeError(
                f"FFmpeg failed to concatenate audio: {result.stderr or result.stdout}"
            )

        if not output_path.exists():
            raise RuntimeError(f"Concatenated audio was not created at {output_path}")

    except subprocess.TimeoutExpired:
        raise RuntimeError("FFmpeg timed out while concatenating audio") from None
    except Exception as e:
        raise RuntimeError(f"FFmpeg error concatenating audio: {e}") from e
    finally:
        # Clean up temp file
        if concat_list_path.exists():
            concat_list_path.unlink()


def normalize_loudness(
    input_path: Union[str, Path], output_path: Union[str, Path], target_lufs: float = -16.0
) -> None:
    """
    Normalize audio loudness using FFmpeg loudnorm filter.

    Args:
        input_path: Path to input audio file
        output_path: Path where to save the normalized audio
        target_lufs: Target integrated loudness in LUFS (default -16.0, YouTube standard)

    Raises:
        RuntimeError: If FFmpeg fails to normalize audio
        FileNotFoundError: If input file doesn't exist
    """
    input_path = Path(input_path)
    output_path = Path(output_path)

    if not input_path.exists():
        raise FileNotFoundError(f"Input audio file not found: {input_path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        result = subprocess.run(
            [
                "ffmpeg",
                "-i", str(input_path),
                "-af", f"loudnorm=I={target_lufs}:TP=-1.5:LRA=11",
                "-y",  # Overwrite if exists
                str(output_path),
            ],
            capture_output=True,
            text=True,
            timeout=600,  # 10 minutes max for normalization
        )

        if result.returncode != 0:
            raise RuntimeError(
                f"FFmpeg failed to normalize loudness: {result.stderr or result.stdout}"
            )

        if not output_path.exists():
            raise RuntimeError(f"Normalized audio was not created at {output_path}")

    except subprocess.TimeoutExpired:
        raise RuntimeError("FFmpeg timed out while normalizing loudness") from None
    except Exception as e:
        raise RuntimeError(f"FFmpeg error normalizing loudness: {e}") from e


def create_video_from_image_and_audio(
    image_path: Union[str, Path],
    audio_path: Union[str, Path],
    output_path: Union[str, Path],
    width: int = 1920,
    height: int = 1080,
    fps: int = 30,
) -> None:
    """
    Create an MP4 video by looping a static image and muxing with audio.

    Args:
        image_path: Path to background image
        audio_path: Path to audio file
        output_path: Path where to save the output MP4
        width: Video width in pixels (default 1920)
        height: Video height in pixels (default 1080)
        fps: Video frame rate (default 30)

    Raises:
        RuntimeError: If FFmpeg fails to create video
        FileNotFoundError: If input files don't exist
    """
    image_path = Path(image_path)
    audio_path = Path(audio_path)
    output_path = Path(output_path)

    if not image_path.exists():
        raise FileNotFoundError(f"Image file not found: {image_path}")
    if not audio_path.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        # Get audio duration to determine loop duration
        # Use ffprobe to get duration
        probe_result = subprocess.run(
            [
                "ffprobe",
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                str(audio_path),
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )

        if probe_result.returncode != 0:
            raise RuntimeError(
                f"Failed to get audio duration: {probe_result.stderr or probe_result.stdout}"
            )

        duration = float(probe_result.stdout.strip())

        # Create video by looping image for the duration of the audio
        result = subprocess.run(
            [
                "ffmpeg",
                "-loop", "1",
                "-i", str(image_path),
                "-i", str(audio_path),
                "-c:v", "libx264",
                "-tune", "stillimage",
                "-c:a", "aac",
                "-b:a", "192k",
                "-pix_fmt", "yuv420p",
                "-shortest",
                "-s", f"{width}x{height}",
                "-r", str(fps),
                "-y",  # Overwrite if exists
                str(output_path),
            ],
            capture_output=True,
            text=True,
            timeout=600,  # 10 minutes max
        )

        if result.returncode != 0:
            raise RuntimeError(
                f"FFmpeg failed to create video: {result.stderr or result.stdout}"
            )

        if not output_path.exists():
            raise RuntimeError(f"Video was not created at {output_path}")

    except subprocess.TimeoutExpired:
        raise RuntimeError("FFmpeg timed out while creating video") from None
    except ValueError as e:
        raise RuntimeError(f"Invalid audio duration: {e}") from e
    except Exception as e:
        raise RuntimeError(f"FFmpeg error creating video: {e}") from e


def find_cinzel_font(bold: bool = False) -> Optional[str]:
    """
    Find Cinzel font file on the system.

    Args:
        bold: If True, look for Cinzel-Bold, else Cinzel-Regular

    Returns:
        Path to font file if found, None otherwise
    """
    from pathlib import Path
    
    font_name = "Cinzel-Bold" if bold else "Cinzel-Regular"
    search_paths = [
        Path("/System/Library/Fonts/Supplemental"),
        Path("/Library/Fonts"),
        Path.home() / "Library/Fonts",
        Path("/usr/share/fonts"),
    ]
    
    for search_path in search_paths:
        if not search_path.exists():
            continue
        # Try various extensions
        for ext in [".ttf", ".otf", ".TTF", ".OTF"]:
            font_path = search_path / f"{font_name}{ext}"
            if font_path.exists():
                return str(font_path)
        # Also try lowercase
        for ext in [".ttf", ".otf"]:
            font_path = search_path / f"{font_name.lower()}{ext}"
            if font_path.exists():
                return str(font_path)
    
    return None


def overlay_text_on_image(
    image_path: Union[str, Path],
    output_path: Union[str, Path],
    title: str,
    channel_title: str,
    width: int = 1920,
    height: int = 1080,
    thumbnail_style: Optional[object] = None,  # ThumbnailStyle from channel config
    custom_font_path: Optional[Union[str, Path]] = None,
) -> None:
    """
    Overlay text on an image using FFmpeg drawtext filter with channel-aware styling.

    Args:
        image_path: Path to input image
        output_path: Path where to save the output image with text overlay
        title: Main title text (already processed with caps and letter spacing)
        channel_title: Channel title text (already processed with caps and letter spacing)
        width: Image width in pixels (default 1920)
        height: Image height in pixels (default 1080)
        thumbnail_style: Optional ThumbnailStyle config from channel
        custom_font_path: Optional path to custom font file (from brand folder)

    Raises:
        RuntimeError: If FFmpeg fails to overlay text
        FileNotFoundError: If input image doesn't exist
    """
    from typing import Optional
    image_path = Path(image_path)
    output_path = Path(output_path)

    if not image_path.exists():
        raise FileNotFoundError(f"Image file not found: {image_path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Determine font files to use
    # Priority: custom_font_path > find_cinzel > system fallback
    title_font_file_path = None
    subtitle_font_file_path = None
    
    if custom_font_path and Path(custom_font_path).exists():
        # Use custom font for both title and subtitle
        title_font_file_path = str(custom_font_path)
        subtitle_font_file_path = str(custom_font_path)
    else:
        # Find Cinzel fonts
        cinzel_bold = find_cinzel_font(bold=True)
        cinzel_regular = find_cinzel_font(bold=False)
        
        # Fallback to system serif fonts if Cinzel not found
        if not cinzel_bold:
            # Try common serif fonts on macOS
            fallback_fonts = [
                "/System/Library/Fonts/Supplemental/Times New Roman Bold.ttf",
                "/System/Library/Fonts/Supplemental/Times.ttc",
                "/System/Library/Fonts/Helvetica.ttc",
            ]
            for font in fallback_fonts:
                if Path(font).exists():
                    cinzel_bold = font
                    break
        
        if not cinzel_regular:
            fallback_fonts = [
                "/System/Library/Fonts/Supplemental/Times New Roman.ttf",
                "/System/Library/Fonts/Supplemental/Times.ttc",
                "/System/Library/Fonts/Helvetica.ttc",
            ]
            for font in fallback_fonts:
                if Path(font).exists():
                    cinzel_regular = font
                    break
        
        title_font_file_path = cinzel_bold
        subtitle_font_file_path = cinzel_regular

    # Escape special characters for FFmpeg drawtext filter
    def escape_text(text: str) -> str:
        """Escape special characters for FFmpeg drawtext."""
        # Escape backslashes, colons, quotes, and equals
        text = text.replace("\\", "\\\\")
        text = text.replace(":", "\\:")
        text = text.replace("'", "\\'")
        text = text.replace('"', '\\"')
        text = text.replace("=", "\\=")
        return text

    title_escaped = escape_text(title)
    channel_title_escaped = escape_text(channel_title)

    # Extract border and shadow values as constants
    # These affect the actual rendered width and must be accounted for
    border_width = 2  # borderw=2 adds 2px on each side = 4px total
    shadow_x = 2  # shadowx=2 extends the rendered width by 2px
    shadow_y = 4  # shadowy=4 (vertical, doesn't affect width calculation)
    
    # Calculate safe margins accounting for border and shadow
    # Base margin: 100px on each side
    # Additional: border (2px * 2 = 4px) + shadow (2px) = 6px per side
    # Total: 106px margin on each side = 212px total
    margin_per_side = 106
    available_width = width - (margin_per_side * 2)
    
    # Get font sizes from thumbnail_style if provided, otherwise calculate
    if thumbnail_style and hasattr(thumbnail_style, "font_size_title") and thumbnail_style.font_size_title:
        title_font_size = thumbnail_style.font_size_title
    else:
        # Estimate character width: with letter spacing, each character is roughly 1.15x font size
        # Use 1.15x instead of 1.2x for more conservative estimation (accounts for font variations)
        # For title: start with 75px, scale down if needed
        title_base_size = 75
        title_char_count = len(title)
        # Account for border (2px * 2 = 4px) and shadow (2px) in width estimation
        # Approximate: with spacing, width ≈ (char_count * fontsize * 1.15) + (borderw * 2) + abs(shadowx)
        title_estimated_width = (title_char_count * title_base_size * 1.15) + (border_width * 2) + abs(shadow_x)
        if title_estimated_width > available_width:
            # Calculate font size that fits: (available_width - border - shadow) / (char_count * 1.15)
            title_font_size = int((available_width - (border_width * 2) - abs(shadow_x)) / (title_char_count * 1.15))
            title_font_size = max(30, title_font_size)  # Minimum 30px
        else:
            title_font_size = title_base_size
    
    if thumbnail_style and hasattr(thumbnail_style, "font_size_subtitle") and thumbnail_style.font_size_subtitle:
        subtitle_font_size = thumbnail_style.font_size_subtitle
    else:
        # For subtitle: start with 55px, scale down if needed
        subtitle_base_size = 55
        subtitle_char_count = len(channel_title)
        # Account for border and shadow in width estimation
        subtitle_estimated_width = (subtitle_char_count * subtitle_base_size * 1.15) + (border_width * 2) + abs(shadow_x)
        if subtitle_estimated_width > available_width:
            # Calculate font size that fits: (available_width - border - shadow) / (char_count * 1.15)
            subtitle_font_size = int((available_width - (border_width * 2) - abs(shadow_x)) / (subtitle_char_count * 1.15))
            subtitle_font_size = max(25, subtitle_font_size)  # Minimum 25px
        else:
            subtitle_font_size = subtitle_base_size

    # Get text color from thumbnail_style if provided
    text_color = "0xF6F6F0"  # Default warm off-white
    if thumbnail_style and hasattr(thumbnail_style, "text_color") and thumbnail_style.text_color:
        text_color = thumbnail_style.text_color

    # Calculate positions based on layout_variant
    layout_variant = "big_title_small_subtitle"  # Default
    if thumbnail_style and hasattr(thumbnail_style, "layout_variant"):
        layout_variant = thumbnail_style.layout_variant
    
    # FFmpeg clamping margin: accounts for border + shadow + safety buffer
    # This ensures text never touches edges even with font metric variations
    ffmpeg_margin = 10  # 10px margin for clamping (accounts for border 2px*2 + shadow 2px + buffer)
    
    # Clamp x position to ensure text stays within bounds
    # FFmpeg's max/min functions use commas which conflict with filter chain separators
    # Solution: Use if/else expressions with escaped commas, or simplify to centering
    # Since we've improved the width calculation to ensure text fits, we can use simple centering
    # with a safety margin check using if/else
    # Formula: if text would overflow left, use margin; if it would overflow right, use w-text_w-margin; else center
    # Using escaped commas to prevent filter chain parsing issues
    clamped_x_expr = f"if(lt((w-text_w)/2\\,{ffmpeg_margin})\\,{ffmpeg_margin}\\,if(gt((w-text_w)/2\\,w-text_w-{ffmpeg_margin})\\,w-text_w-{ffmpeg_margin}\\,(w-text_w)/2))"
    
    if layout_variant == "centered_title":
        # Both centered, title at 50%, subtitle at 60%
        title_x = clamped_x_expr
        title_y = f"h*0.50"
        subtitle_x = clamped_x_expr
        subtitle_y = f"h*0.60"
    elif layout_variant == "bottom_title":
        # Title at bottom, subtitle above it
        title_x = clamped_x_expr
        title_y = f"h*0.85"
        subtitle_x = clamped_x_expr
        subtitle_y = f"h*0.75"
    else:  # big_title_small_subtitle (default)
        # Main title at 66% down, subtitle at 78% down
        title_x = clamped_x_expr
        title_y = f"h*0.66"
        subtitle_x = clamped_x_expr
        subtitle_y = f"h*0.78"
    
    # Override position if explicitly set in thumbnail_style
    if thumbnail_style and hasattr(thumbnail_style, "text_position") and thumbnail_style.text_position:
        # text_position format: "title_x,title_y,subtitle_x,subtitle_y" or FFmpeg expressions
        # For now, we'll use the calculated positions above
        pass

    # Build drawtext filters with channel-aware styling
    # Note: background_overlay support can be added later if needed
    # For now, we focus on font, size, color, and position customization
    
    # Main title: dynamically sized font with channel styling
    # Note: x and y expressions must be properly formatted for FFmpeg
    # When using expressions with commas (like max(10, min(...))), we need to ensure
    # the filter chain is properly separated
    title_font_file = f":fontfile={title_font_file_path}" if title_font_file_path else ""
    title_filter = (
        f"drawtext=text='{title_escaped}':"
        f"fontsize={title_font_size}:"
        f"fontcolor={text_color}:"
        f"borderw={border_width}:"
        f"bordercolor=black@0.25:"
        f"shadowx={shadow_x}:"
        f"shadowy={shadow_y}:"
        f"shadowcolor=black@0.6:"
        f"x={title_x}:"
        f"y={title_y}"
        f"{title_font_file}"
    )

    # Subtitle: dynamically sized font with channel styling
    subtitle_font_file = f":fontfile={subtitle_font_file_path}" if subtitle_font_file_path else ""
    subtitle_filter = (
        f"drawtext=text='{channel_title_escaped}':"
        f"fontsize={subtitle_font_size}:"
        f"fontcolor={text_color}:"
        f"borderw={border_width}:"
        f"bordercolor=black@0.25:"
        f"shadowx={shadow_x}:"
        f"shadowy={shadow_y}:"
        f"shadowcolor=black@0.6:"
        f"x={subtitle_x}:"
        f"y={subtitle_y}"
        f"{subtitle_font_file}"
    )

    # Combine filters - use semicolon to separate complex filter chains if needed
    # But comma should work for simple chains. The issue might be with expression parsing.
    # Let's try wrapping the x expression in parentheses or using a different approach
    filter_complex = f"{title_filter},{subtitle_filter}"

    try:
        result = subprocess.run(
            [
                "ffmpeg",
                "-i", str(image_path),
                "-vf", filter_complex,
                "-y",  # Overwrite if exists
                str(output_path),
            ],
            capture_output=True,
            text=True,
            timeout=60,  # 1 minute max
        )

        if result.returncode != 0:
            # Try without font files if font specification fails
            # Use the same dynamically calculated font sizes and clamping expressions
            title_filter_fallback = (
                f"drawtext=text='{title_escaped}':"
                f"fontsize={title_font_size}:"
                f"fontcolor=0xF6F6F0:"
                f"borderw={border_width}:"
                f"bordercolor=black@0.25:"
                f"shadowx={shadow_x}:"
                f"shadowy={shadow_y}:"
                f"shadowcolor=black@0.6:"
                f"x={title_x}:"
                f"y={title_y}"
            )
            subtitle_filter_fallback = (
                f"drawtext=text='{channel_title_escaped}':"
                f"fontsize={subtitle_font_size}:"
                f"fontcolor=0xF6F6F0:"
                f"borderw={border_width}:"
                f"bordercolor=black@0.25:"
                f"shadowx={shadow_x}:"
                f"shadowy={shadow_y}:"
                f"shadowcolor=black@0.6:"
                f"x={subtitle_x}:"
                f"y={subtitle_y}"
            )
            filter_complex_fallback = f"{title_filter_fallback},{subtitle_filter_fallback}"

            result = subprocess.run(
                [
                    "ffmpeg",
                    "-i", str(image_path),
                    "-vf", filter_complex_fallback,
                    "-y",
                    str(output_path),
                ],
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode != 0:
                raise RuntimeError(
                    f"FFmpeg failed to overlay text: {result.stderr or result.stdout}"
                )

        if not output_path.exists():
            raise RuntimeError(f"Output image with text overlay was not created at {output_path}")

    except subprocess.TimeoutExpired:
        raise RuntimeError("FFmpeg timed out while overlaying text") from None
    except Exception as e:
        raise RuntimeError(f"FFmpeg error overlaying text: {e}") from e

