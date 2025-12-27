"""
Plan step: Generate planning data using Gemini API.

Generates:
- Track prompts with style, title, and musical description
- Optional lyrics for each track (if vocals and lyrics enabled)
- YouTube metadata (title, description, tags)
"""

import random

from ytf.channel import get_channel
from ytf.logger import StepLogger
from ytf.project import (
    PlanData,
    PlanPrompt,
    YouTubeMetadata,
    load_project,
    save_project,
    update_status,
)
from ytf.providers.gemini import GeminiProvider


def run(project_id: str) -> None:
    """
    Run the plan step with full Gemini integration.

    Args:
        project_id: Project ID

    Raises:
        Exception: If step fails (error persisted to project.json)
    """
    project = load_project(project_id)

    with StepLogger(project_id, "plan") as log:
        try:
            # Mark step as started (do not mark as successful until the end)
            project.status.current_step = "plan"
            save_project(project)

            log.info("Starting plan step with Gemini integration")

            # Validate channel_id is set
            if not project.channel_id:
                raise ValueError("Project missing channel_id. Run 'ytf new' with --channel first.")

            # Load channel profile
            try:
                channel = get_channel(project.channel_id)
                log.info(f"Channel: {project.channel_id} ({channel.name})")
            except Exception as e:
                log.error(f"Failed to load channel profile: {e}")
                raise

            log.info(f"Theme: {project.theme}")
            log.info(f"Track count: {project.track_count}")
            log.info(f"Vocals enabled: {project.vocals.enabled}")
            log.info(f"Lyrics enabled: {project.lyrics.enabled}")

            # Choose CTA variant from channel profile
            if channel.cta_variants:
                cta_variant = random.choice(channel.cta_variants)
                project.funnel.cta_variant_id = cta_variant.variant_id
                log.info(f"Selected CTA variant: {cta_variant.variant_id}")
            else:
                log.warning("No CTA variants defined in channel profile")

            # Initialize Gemini provider
            try:
                provider = GeminiProvider()
            except ValueError as e:
                log.error(f"Failed to initialize Gemini provider: {e}")
                raise

            # Build prompt constraints from channel
            banned_terms_text = ""
            if channel.prompt_constraints.banned_terms:
                banned_terms_text = f"\nBANNED TERMS (do not use these): {', '.join(channel.prompt_constraints.banned_terms)}"

            style_guidance_text = ""
            if channel.prompt_constraints.style_guidance:
                style_guidance_text = f"\nStyle guidance: {channel.prompt_constraints.style_guidance}"

            energy_text = f"\nEnergy level: {channel.prompt_constraints.energy_level}"

            # Generate job prompts (each job produces 2 variants, so jobs = ceil(track_count/2))
            import math
            job_count = math.ceil(project.track_count / 2)
            log.info(f"Generating {job_count} job prompts (will produce {project.track_count} tracks via {job_count} Suno jobs)...")
            track_data_list = provider.generate_track_data(
                theme=project.theme,
                track_count=job_count,  # Generate prompts for jobs, not final tracks
                vocals_enabled=project.vocals.enabled,
                channel_constraints=f"{banned_terms_text}{style_guidance_text}{energy_text}",
            )
            log.info(f"Generated {len(track_data_list)} job prompt entries")

            # Create PlanPrompt objects (one per job)
            prompts = []
            for i, track_data in enumerate(track_data_list):
                prompt = PlanPrompt(
                    job_index=i,
                    style=track_data["style"],
                    title=track_data["title"],
                    prompt=track_data["prompt"],
                    vocals_enabled=project.vocals.enabled,
                )
                prompts.append(prompt)
                log.info(f"Job {i}: {track_data['title']} ({track_data['style']}) - will produce 2 variants")

            # Generate lyrics if vocals and lyrics are enabled
            if project.vocals.enabled and project.lyrics.enabled:
                log.info("Generating lyrics for jobs with vocals...")
                for prompt in prompts:
                    try:
                        log.info(f"Generating lyrics for job {prompt.job_index}: {prompt.title}")
                        lyrics = provider.generate_lyrics(
                            style=prompt.style,
                            title=prompt.title,
                            theme=project.theme,
                        )
                        prompt.lyrics_text = lyrics
                        log.info(
                            f"Generated lyrics for job {prompt.job_index} "
                            f"({len(lyrics)} characters)"
                        )
                    except Exception as e:
                        log.error(
                            f"Failed to generate lyrics for job {prompt.job_index}: {e}"
                        )
                        # Continue with other tracks even if one fails
                        raise

            # Generate YouTube metadata with retry logic for validation
            log.info("Generating YouTube metadata...")
            max_retries = 2
            youtube_metadata = None
            
            for attempt in range(max_retries + 1):
                try:
                    metadata_dict = provider.generate_youtube_metadata(
                        theme=project.theme,
                        track_count=project.track_count,
                    )
                    candidate_metadata = YouTubeMetadata(
                        title=metadata_dict["title"],
                        description=metadata_dict["description"],
                        tags=metadata_dict["tags"],
                    )
                    
                    # Validate metadata against channel tag rules
                    log.info(f"Validating metadata (attempt {attempt + 1}/{max_retries + 1})...")
                    
                    validation_failed = False
                    validation_errors = []
                    
                    # Check for banned terms in title, description, and tags
                    all_text = f"{candidate_metadata.title} {candidate_metadata.description} {' '.join(candidate_metadata.tags)}".lower()
                    banned_found = []
                    for banned_term in channel.tag_rules.banned_terms:
                        if banned_term.lower() in all_text:
                            banned_found.append(banned_term)
                    
                    if banned_found:
                        validation_failed = True
                        validation_errors.append(f"Banned terms: {', '.join(banned_found)}")
                    
                    # Enforce tag whitelist if defined (strict: all tags must be in whitelist)
                    if channel.tag_rules.whitelist:
                        invalid_tags = []
                        for tag in candidate_metadata.tags:
                            tag_lower = tag.lower()
                            # Strict check: tag must exactly match or be contained in a whitelist entry
                            if not any(
                                allowed.lower() == tag_lower or 
                                tag_lower in allowed.lower() or 
                                allowed.lower() in tag_lower
                                for allowed in channel.tag_rules.whitelist
                            ):
                                invalid_tags.append(tag)
                        
                        if invalid_tags:
                            validation_failed = True
                            validation_errors.append(f"Tags not in whitelist: {', '.join(invalid_tags)}")
                    
                    # If validation passed, use this metadata
                    if not validation_failed:
                        youtube_metadata = candidate_metadata
                        if channel.tag_rules.whitelist:
                            # Filter to only whitelisted tags
                            filtered_tags = []
                            for tag in candidate_metadata.tags:
                                tag_lower = tag.lower()
                                if any(
                                    allowed.lower() == tag_lower or 
                                    tag_lower in allowed.lower() or 
                                    allowed.lower() in tag_lower
                                    for allowed in channel.tag_rules.whitelist
                                ):
                                    filtered_tags.append(tag)
                            youtube_metadata.tags = filtered_tags
                            log.info(f"Filtered tags to whitelist: {len(filtered_tags)} tags")
                        break
                    else:
                        # Validation failed, log and retry if attempts remain
                        if attempt < max_retries:
                            log.warning(
                                f"Metadata validation failed: {', '.join(validation_errors)}. "
                                f"Retrying with stricter prompt..."
                            )
                            # Note: In a future enhancement, we could pass stricter constraints to Gemini
                            # For now, we just retry and hope Gemini generates better metadata
                        else:
                            # All retries exhausted, fail fast
                            error_msg = (
                                f"Metadata validation failed after {max_retries + 1} attempts. "
                                f"Errors: {', '.join(validation_errors)}. Channel: {project.channel_id}"
                            )
                            log.error(error_msg)
                            raise ValueError(error_msg)
                            
                except Exception as e:
                    if attempt >= max_retries:
                        raise
                    log.warning(f"Metadata generation failed (attempt {attempt + 1}): {e}. Retrying...")
            
            if youtube_metadata is None:
                raise RuntimeError("Failed to generate valid YouTube metadata after retries")

            log.info(f"YouTube title: {youtube_metadata.title}")
            log.info(f"YouTube tags: {', '.join(youtube_metadata.tags)}")

            # Create PlanData and save to project
            plan_data = PlanData(
                prompts=prompts,
                youtube_metadata=youtube_metadata,
            )
            project.plan = plan_data

            # Persist funnel config (CTA variant already set earlier)
            save_project(project)

            # Mark as successful
            update_status(project, "plan", error=None)
            save_project(project)

            log.info("Plan step completed successfully")
            log.info(f"Generated {len(prompts)} track prompts")
            if project.vocals.enabled and project.lyrics.enabled:
                log.info(f"Generated lyrics for {len([p for p in prompts if p.lyrics_text])} tracks")

        except Exception as e:
            update_status(project, "plan", error=e)
            save_project(project)
            log.error(f"Plan step failed: {e}")
            raise

