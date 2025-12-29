"""
Render step: Render final video using FFmpeg.

Concatenates all available tracks, normalizes audio, and creates MP4 with static background.
"""

import subprocess
from pathlib import Path

from ytf.channel import get_channel
from ytf.logger import StepLogger
from ytf.project import PROJECTS_DIR, RenderData, load_project, save_project, update_status
from ytf.providers.gemini import GeminiProvider
from ytf.utils import ffmpeg


def format_timestamp(seconds: float) -> str:
    """
    Format seconds as YouTube chapter timestamp (MM:SS or HH:MM:SS).

    Args:
        seconds: Duration in seconds

    Returns:
        Formatted timestamp string
    """
    total_seconds = int(seconds)
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    secs = total_seconds % 60

    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def clean_title(title: str) -> str:
    """
    Clean album title by removing track count patterns.

    Args:
        title: Original title

    Returns:
        Cleaned title without track count
    """
    import re
    # Remove patterns like "(2 Tracks)", "(25 Tracks)", etc.
    cleaned = re.sub(r'\s*\(\d+\s+[Tt]racks?\)\s*', '', title)
    # Clean up extra whitespace
    cleaned = ' '.join(cleaned.split())
    return cleaned


def add_letter_spacing(text: str) -> str:
    """
    Add wide letter spacing by inserting spaces between letters.

    Args:
        text: Text to process

    Returns:
        Text with spaces between each letter
    """
    # Insert space between each character, but preserve existing spaces
    # Split by spaces first, then add spacing within each word
    words = text.split()
    spaced_words = []
    for word in words:
        spaced_word = ' '.join(word)
        spaced_words.append(spaced_word)
    return '   '.join(spaced_words)  # Triple space between words


def get_channel_title() -> str:
    """
    Get channel title from environment or return default.

    Returns:
        Channel title string
    """
    import os
    from dotenv import load_dotenv
    load_dotenv()
    channel_title = os.getenv("YOUTUBE_CHANNEL_TITLE", "Music Channel")
    return channel_title


def run(project_id: str) -> None:
    """
    Run the render step.

    Args:
        project_id: Project ID

    Raises:
        Exception: If step fails (error persisted to project.json)
    """
    project = load_project(project_id)
    project_dir = PROJECTS_DIR / project_id

    with StepLogger(project_id, "render") as log:
        try:
            # Mark step as started (do not mark as successful until the end)
            project.status.current_step = "render"
            save_project(project)

            log.info("Starting render step")

            # Validate FFmpeg is available
            if not ffmpeg.check_ffmpeg():
                raise RuntimeError("FFmpeg is not available. Run 'ytf doctor' to check prerequisites.")

            # Load channel profile for target duration check
            channel = None
            if project.channel_id:
                try:
                    channel = get_channel(project.channel_id)
                    log.info(f"Channel: {project.channel_id} ({channel.name})")
                except Exception as e:
                    log.warning(f"Failed to load channel profile: {e}")

            # Track selection logic: honor approvals/QC
            approved_path = project_dir / "approved.txt"
            approved_indices = set()

            if approved_path.exists():
                log.info(f"Reading approved.txt: {approved_path}")
                with open(approved_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#"):
                            try:
                                idx = int(line)
                                approved_indices.add(idx)
                            except ValueError:
                                log.warning(f"Invalid track index in approved.txt: {line}")

            # Filter tracks based on approval/QC status
            if approved_indices:
                # Use only approved tracks (still require status=="ok" and file exists)
                log.info(f"Using approved tracks from approved.txt: {sorted(approved_indices)}")
                available_tracks = [
                    track
                    for track in project.tracks
                    if track.status == "ok"
                    and track.audio_path is not None
                    and track.track_index in approved_indices
                ]
            else:
                # Use QC-passed tracks
                log.info("No approved.txt found, using QC-passed tracks")
                available_tracks = [
                    track
                    for track in project.tracks
                    if track.status == "ok"
                    and track.audio_path is not None
                    and (track.qc is None or track.qc.passed)
                ]

            if not available_tracks:
                error_msg = "No available tracks to render. All tracks are failed, missing audio files, or failed QC."
                if approved_indices:
                    error_msg += f" Approved tracks: {sorted(approved_indices)}"
                raise RuntimeError(error_msg)

            # Sort by track_index to maintain order
            available_tracks.sort(key=lambda t: t.track_index)

            log.info(f"Found {len(available_tracks)} available tracks")
            total_duration = sum(track.duration_seconds for track in available_tracks)
            log.info(f"Total duration: {format_timestamp(total_duration)} ({total_duration:.2f} seconds)")

            # Check if duration meets target/minimum (fail fast if underfilled)
            # project.json is the source of truth; channel profile provides defaults.
            target_minutes = project.target_minutes
            min_minutes = None
            if channel:
                if target_minutes is None:
                    target_minutes = channel.duration_rules.target_minutes
                min_minutes = channel.duration_rules.min_minutes

            if target_minutes is None:
                # Should not happen (new step always sets it), but keep render defensive.
                target_minutes = 60

            target_seconds = target_minutes * 60
            min_seconds = None
            if min_minutes is not None:
                # If user explicitly created a shorter project than the channel minimum,
                # honor the project and don't block render with an impossible minimum.
                if project.target_minutes is not None and project.target_minutes < min_minutes:
                    log.warning(
                        f"Project target_minutes ({project.target_minutes}) is below channel min_minutes "
                        f"({min_minutes}). Honoring project.json for this render."
                    )
                    min_minutes = project.target_minutes
                min_seconds = (min_minutes or 0) * 60

            if min_seconds is not None and total_duration < min_seconds:
                    missing_seconds = min_seconds - total_duration
                    missing_minutes = missing_seconds / 60
                    error_msg = (
                        f"Insufficient track duration: {total_duration:.2f}s ({total_duration/60:.1f} min) "
                        f"is below minimum {min_seconds}s ({min_minutes} min). "
                        f"Need {missing_seconds:.2f}s ({missing_minutes:.1f} min) more. "
                        f"Channel: {project.channel_id}"
                    )
                    log.error(error_msg)
                    raise RuntimeError(error_msg)

            if total_duration < target_seconds:
                missing_seconds = target_seconds - total_duration
                missing_minutes = missing_seconds / 60
                log.warning(
                    f"Total duration {total_duration:.2f}s ({total_duration/60:.1f} min) "
                    f"is below target {target_seconds}s ({target_minutes} min). "
                    f"Missing {missing_seconds:.2f}s ({missing_minutes:.1f} min)."
                )

            # Get track indices for persistence
            selected_indices = [track.track_index for track in available_tracks]

            # Prepare paths
            tracks_dir = project_dir / "tracks"
            output_dir = project_dir / "output"
            assets_dir = project_dir / "assets"
            output_dir.mkdir(exist_ok=True)

            # Step 1: Concatenate audio files
            log.info("Concatenating audio tracks...")
            concat_audio_path = output_dir / "concat_audio.mp3"
            audio_file_paths = [
                project_dir / track.audio_path
                for track in available_tracks
            ]
            ffmpeg.concatenate_audio_files(audio_file_paths, concat_audio_path)
            log.info(f"Concatenated audio saved to {concat_audio_path}")

            # Step 2: Normalize loudness
            log.info("Normalizing audio loudness...")
            normalized_audio_path = output_dir / "normalized_audio.mp3"
            ffmpeg.normalize_loudness(concat_audio_path, normalized_audio_path)
            log.info(f"Normalized audio saved to {normalized_audio_path}")

            # Step 3: Handle background image (always per-project; hard gate for upload)
            # We want each YouTube video to have its own image generated for that project.
            background_path = assets_dir / "background.png"

            if background_path.exists():
                log.info(f"Using existing project background: {background_path}")
            else:
                log.info("Generating background image with Gemini...")
                provider = GeminiProvider()

                # Build channel-aware prompt
                generation_theme = project.theme
                if channel:
                    if channel.prompt_constraints.style_guidance:
                        generation_theme = (
                            f"{project.theme}. {channel.prompt_constraints.style_guidance}"
                        )
                    if channel.intent:
                        generation_theme = f"{generation_theme} (Intent: {channel.intent})"

                provider.generate_background_image(
                    theme=generation_theme,
                    output_path=str(background_path),
                )

                if not background_path.exists():
                    raise RuntimeError(
                        f"Gemini did not create background image at {background_path}"
                    )
                log.info(f"Generated background image using Gemini at {background_path}")

            # Step 3.5: Create thumbnail with text overlay
            log.info("Creating thumbnail with text overlay...")
            thumbnail_path = assets_dir / "thumbnail.png"
            
            # Get and process album title
            album_title = "Music Compilation"
            if project.plan and project.plan.youtube_metadata:
                album_title = project.plan.youtube_metadata.title
            
            # Check for safe words and sanitize if needed
            if channel and channel.thumbnail_style.safe_words:
                original_title = album_title
                for safe_word in channel.thumbnail_style.safe_words:
                    if safe_word.lower() in album_title.lower():
                        log.warning(
                            f"Title contains safe word '{safe_word}', sanitizing: {album_title}"
                        )
                        # Remove safe word (case-insensitive)
                        import re
                        album_title = re.sub(
                            re.escape(safe_word), "", album_title, flags=re.IGNORECASE
                        )
                        album_title = " ".join(album_title.split())  # Clean up extra spaces
                        log.info(f"Sanitized title: {album_title}")
                        break
            
            # Clean title (remove track count) and process
            cleaned_title = clean_title(album_title)
            title_uppercase = cleaned_title.upper()
            title_spaced = add_letter_spacing(title_uppercase)
            
            # Get channel title and process
            # Subtitle source:
            # - Prefer `project.json.channel.title` when present (some project.json files may embed this).
            # - Otherwise, fall back to channel profile name when available.
            # - Otherwise, omit subtitle (do not fall back to env var/defaults for this style).
            channel_spaced = None
            subtitle_raw = None
            try:
                import json

                raw_project_path = project_dir / "project.json"
                with open(raw_project_path, "r", encoding="utf-8") as f:
                    raw_project = json.load(f)
                raw_channel = raw_project.get("channel") or {}
                if isinstance(raw_channel, dict):
                    subtitle_raw = raw_channel.get("title") or raw_channel.get("name")
            except Exception:
                subtitle_raw = None

            if not subtitle_raw and channel and channel.name:
                subtitle_raw = channel.name

            if subtitle_raw:
                channel_spaced = add_letter_spacing(str(subtitle_raw).upper())
            
            # Get thumbnail style from channel config
            thumbnail_style = None
            if channel:
                thumbnail_style = channel.thumbnail_style
            
            # Check for custom font in brand folder
            custom_font_path = None
            if project.channel_id:
                repo_root = PROJECTS_DIR.parent  # Go up from projects/ to repo root
                brand_dir = repo_root / "assets" / "brand" / project.channel_id
                for font_ext in [".ttf", ".otf"]:
                    font_path = brand_dir / f"font{font_ext}"
                    if font_path.exists():
                        custom_font_path = font_path
                        log.info(f"Using custom font from brand folder: {font_path}")
                        break
            
            ffmpeg.overlay_text_on_image(
                image_path=background_path,
                output_path=thumbnail_path,
                title=title_spaced,
                channel_title=channel_spaced,
                width=project.video.width,
                height=project.video.height,
                thumbnail_style=thumbnail_style,
                custom_font_path=custom_font_path,
            )
            if not thumbnail_path.exists():
                raise RuntimeError(f"Thumbnail file was not created at {thumbnail_path}")

            log.info(f"Thumbnail with text overlay saved to {thumbnail_path}")
            thumbnail_created = True

            # Step 4: Create video
            log.info("Creating video with static background...")
            final_video_path = output_dir / "final.mp4"
            ffmpeg.create_video_from_image_and_audio(
                background_path,
                normalized_audio_path,
                final_video_path,
                width=project.video.width,
                height=project.video.height,
                fps=project.video.fps,
            )
            log.info(f"Final video saved to {final_video_path}")

            # Step 5: Generate chapters
            log.info("Generating chapters...")
            chapters_path = output_dir / "chapters.txt"
            chapters_lines = []
            cumulative_time = 0.0

            for track in available_tracks:
                timestamp = format_timestamp(cumulative_time)
                # Use Track.title if available (includes variant suffix like "Title I" or "Title II"),
                # otherwise fallback to track index
                if hasattr(track, 'title') and track.title:
                    title = track.title
                else:
                    # Fallback for backwards compatibility
                    title = f"Track {track.track_index + 1}"
                chapters_lines.append(f"{timestamp} {title}")
                cumulative_time += track.duration_seconds

            with open(chapters_path, "w", encoding="utf-8") as f:
                f.write("\n".join(chapters_lines))
                f.write("\n")

            log.info(f"Chapters saved to {chapters_path}")

            # Step 6: Generate YouTube description with channel template + CTA
            log.info("Generating YouTube description...")
            description_path = output_dir / "youtube_description.txt"

            # Load channel profile for template
            channel = None
            if project.channel_id:
                try:
                    channel = get_channel(project.channel_id)
                except Exception as e:
                    log.warning(f"Failed to load channel profile: {e}, using fallback description")

            # Format chapters text
            chapters_text = "\n".join(chapters_lines)

            # Build CTA block
            cta_text = ""
            if channel and project.funnel.cta_variant_id:
                # Find matching CTA variant
                cta_variant = None
                for variant in channel.cta_variants:
                    if variant.variant_id == project.funnel.cta_variant_id:
                        cta_variant = variant
                        break

                if cta_variant:
                    # Format CTA with UTM parameters
                    landing_url = project.funnel.landing_url or "{landing_url}"
                    utm_source = project.funnel.utm_source or "{utm_source}"
                    utm_campaign = project.funnel.utm_campaign or "{utm_campaign}"
                    
                    cta_long = cta_variant.long_text.format(
                        landing_url=landing_url,
                        utm_source=utm_source,
                        utm_campaign=utm_campaign,
                    )
                    cta_text = cta_long
                else:
                    log.warning(f"CTA variant {project.funnel.cta_variant_id} not found in channel profile")
            elif channel and channel.description_template.cta_block:
                # Fallback to channel default CTA block
                landing_url = project.funnel.landing_url or "{landing_url}"
                utm_source = project.funnel.utm_source or "{utm_source}"
                utm_campaign = project.funnel.utm_campaign or "{utm_campaign}"
                cta_text = channel.description_template.cta_block.format(
                    landing_url=landing_url,
                    utm_source=utm_source,
                    utm_campaign=utm_campaign,
                )

            # Use channel template if available
            if channel and channel.description_template.template:
                description_text = channel.description_template.template.format(
                    theme=project.theme,
                    chapters=chapters_text,
                    cta=cta_text,
                )
            else:
                # Fallback to simple description
                description_lines = []
                if project.plan and project.plan.youtube_metadata:
                    description_lines.append(project.plan.youtube_metadata.description)
                else:
                    description_lines.append("Music compilation")

                description_lines.append("")
                description_lines.append("Chapters:")
                description_lines.extend(chapters_lines)
                if cta_text:
                    description_lines.append("")
                    description_lines.append(cta_text)
                description_text = "\n".join(description_lines)

            with open(description_path, "w", encoding="utf-8") as f:
                f.write(description_text)
                f.write("\n")

            log.info(f"YouTube description saved to {description_path}")

            # Step 6.5: Generate pinned comment
            log.info("Generating pinned comment...")
            pinned_comment_path = output_dir / "pinned_comment.txt"

            pinned_comment_lines = []
            if channel and project.funnel.cta_variant_id:
                # Find matching CTA variant
                cta_variant = None
                for variant in channel.cta_variants:
                    if variant.variant_id == project.funnel.cta_variant_id:
                        cta_variant = variant
                        break

                if cta_variant:
                    landing_url = project.funnel.landing_url or "{landing_url}"
                    utm_source = project.funnel.utm_source or "{utm_source}"
                    utm_campaign = project.funnel.utm_campaign or "{utm_campaign}"
                    
                    # Format both variants
                    cta_short = cta_variant.short_text.format(
                        landing_url=landing_url,
                        utm_source=utm_source,
                        utm_campaign=utm_campaign,
                    )
                    cta_long = cta_variant.long_text.format(
                        landing_url=landing_url,
                        utm_source=utm_source,
                        utm_campaign=utm_campaign,
                    )
                    
                    pinned_comment_lines.append("=== SHORT VARIANT ===")
                    pinned_comment_lines.append(cta_short)
                    pinned_comment_lines.append("")
                    pinned_comment_lines.append("=== LONG VARIANT ===")
                    pinned_comment_lines.append(cta_long)
                else:
                    log.warning(f"CTA variant {project.funnel.cta_variant_id} not found for pinned comment")
                    pinned_comment_lines.append("(No CTA variant configured)")

            if not pinned_comment_lines:
                pinned_comment_lines.append("(No pinned comment configured)")

            with open(pinned_comment_path, "w", encoding="utf-8") as f:
                f.write("\n".join(pinned_comment_lines))
                f.write("\n")

            log.info(f"Pinned comment saved to {pinned_comment_path}")

            # Step 7: Persist render data to project.json
            thumbnail_path_str = None
            if thumbnail_created and thumbnail_path.exists():
                thumbnail_path_str = str(thumbnail_path.relative_to(project_dir))
            
            project.render = RenderData(
                background_path=str(background_path.relative_to(project_dir)),
                thumbnail_path=thumbnail_path_str,
                selected_track_indices=selected_indices,
                output_mp4_path=str(final_video_path.relative_to(project_dir)),
                chapters_path=str(chapters_path.relative_to(project_dir)),
                description_path=str(description_path.relative_to(project_dir)),
            )

            # Clean up intermediate files
            log.info("Cleaning up intermediate files...")
            if concat_audio_path.exists():
                concat_audio_path.unlink()
            if normalized_audio_path.exists():
                normalized_audio_path.unlink()

            # Mark as successful
            update_status(project, "render", error=None)
            save_project(project)

            log.info("Render step completed successfully")
            log.info(f"Output files:")
            log.info(f"  - Video: {final_video_path}")
            log.info(f"  - Chapters: {chapters_path}")
            log.info(f"  - Description: {description_path}")
            log.info(f"  - Pinned comment: {pinned_comment_path}")

        except Exception as e:
            update_status(project, "render", error=e)
            save_project(project)
            log.error(f"Render step failed: {e}")
            raise
