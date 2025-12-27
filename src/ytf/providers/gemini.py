"""
Gemini provider: generates track prompts, lyrics, and YouTube metadata.

Uses Google's Gemini API via the google-genai package.
All API calls use the gemini-2.5-flash model for speed and cost-effectiveness.
"""

import json
import os
from typing import Any

from dotenv import load_dotenv
from google import genai
from google.api_core import exceptions as google_exceptions

from ytf.utils.retry import retry_call

# Load environment variables from .env file
load_dotenv()


class GeminiProvider:
    """Wrapper for Gemini API calls."""

    def __init__(self):
        """
        Initialize Gemini client.

        Raises:
            ValueError: If GEMINI_API_KEY is not set
        """
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError(
                "GEMINI_API_KEY environment variable is not set. "
                "Please set it in your .env file."
            )
        self.client = genai.Client()
        self.model = "gemini-2.5-flash"

    def generate_track_data(
        self, theme: str, track_count: int, vocals_enabled: bool, channel_constraints: str = ""
    ) -> list[dict[str, str]]:
        """
        Generate track data (style, title, prompt) for all tracks in one API call.

        Args:
            theme: Project theme
            track_count: Number of tracks to generate
            vocals_enabled: Whether tracks should include vocals
            channel_constraints: Additional channel-specific constraints (banned terms, style guidance, etc.)

        Returns:
            List of dicts with keys: 'style', 'title', 'prompt'

        Raises:
            Exception: If API call fails or response is invalid
        """
        vocals_desc = "Include description of vocal style" if vocals_enabled else "Instrumental only"

        prompt = f"""Generate {track_count} music tracks for a compilation with theme: "{theme}".

For each track, generate:
1. style: Music genre/style (e.g., "Ambient", "Electronic", "Jazz") - max 1000 characters
2. title: Track title - max 100 characters
3. prompt: Musical description with mood, instrumentation, tempo - max 5000 characters
   {vocals_desc}

Requirements:
- Stay consistent with theme
- Use tight variations (re-use motifs for coherence)
- NO artist references
- NO copyrighted lyrics
- NO brand names{channel_constraints}

Return JSON array: [{{"style": "...", "title": "...", "prompt": "..."}}, ...]
Make sure the JSON is valid and parseable."""

        try:
            # Wrap API call with retry logic
            response = retry_call(
                lambda: self.client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                ),
                max_retries=3,
                initial_delay=1.0,
            )

            # Extract text from response
            response_text = response.text.strip()

            # Try to extract JSON from markdown code blocks if present
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()

            # Parse JSON
            track_data = json.loads(response_text)

            if not isinstance(track_data, list):
                raise ValueError(f"Expected list, got {type(track_data)}")

            if len(track_data) != track_count:
                raise ValueError(
                    f"Expected {track_count} tracks, got {len(track_data)}"
                )

            # Validate each track
            for i, track in enumerate(track_data):
                if not isinstance(track, dict):
                    raise ValueError(f"Track {i} is not a dict: {track}")
                if "style" not in track or "title" not in track or "prompt" not in track:
                    raise ValueError(f"Track {i} missing required fields: {track}")

                # Validate character limits
                style = str(track["style"]).strip()
                title = str(track["title"]).strip()
                prompt_text = str(track["prompt"]).strip()

                if not style or len(style) > 1000:
                    raise ValueError(
                        f"Track {i} style invalid: length {len(style)}, max 1000"
                    )
                if not title or len(title) > 100:
                    raise ValueError(
                        f"Track {i} title invalid: length {len(title)}, max 100"
                    )
                if not prompt_text or len(prompt_text) > 5000:
                    raise ValueError(
                        f"Track {i} prompt invalid: length {len(prompt_text)}, max 5000"
                    )

                track["style"] = style
                track["title"] = title
                track["prompt"] = prompt_text

            return track_data

        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse JSON response: {e}\nResponse: {response_text}") from e
        except google_exceptions.GoogleAPIError as e:
            # Preserve raw error details
            raw_error = f"Google API error: {str(e)}"
            if hasattr(e, "status_code"):
                raw_error = f"HTTP {e.status_code}: {raw_error}"
            raise RuntimeError(f"Gemini API error: {e} | Raw: {raw_error}") from e
        except Exception as e:
            # Preserve raw error details
            raw_error = str(e)
            if hasattr(e, "response"):
                raw_error = f"Response: {getattr(e.response, 'text', raw_error)}"
            raise RuntimeError(f"Gemini API error: {e} | Raw: {raw_error}") from e

    def generate_lyrics(self, style: str, title: str, theme: str) -> str:
        """
        Generate original lyrics for a track.

        Args:
            style: Music style/genre
            title: Track title
            theme: Project theme

        Returns:
            Lyrics text (max 5000 characters)

        Raises:
            Exception: If API call fails
        """
        prompt = f"""Generate original lyrics for a music track.

Style: {style}
Title: {title}
Theme: {theme}

Requirements:
- Original lyrics (no quotes from existing songs)
- No references to real artists
- No brand names
- Simple chorus structure for listenability
- Match the style and mood
- Format suitable for Suno API (will be used as exact lyrics)
- Max 5000 characters

Return only the lyrics text, no explanations. Use [Verse], [Chorus] tags if needed."""

        try:
            # Wrap API call with retry logic
            response = retry_call(
                lambda: self.client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                ),
                max_retries=3,
                initial_delay=1.0,
            )

            lyrics = response.text.strip()

            # Remove markdown code blocks if present
            if "```" in lyrics:
                lyrics = lyrics.split("```")[1].split("```")[0].strip()

            # Validate length
            if len(lyrics) > 5000:
                raise ValueError(f"Lyrics too long: {len(lyrics)} characters, max 5000")

            if not lyrics:
                raise ValueError("Generated lyrics are empty")

            return lyrics

        except google_exceptions.GoogleAPIError as e:
            raw_error = f"Google API error: {str(e)}"
            if hasattr(e, "status_code"):
                raw_error = f"HTTP {e.status_code}: {raw_error}"
            raise RuntimeError(f"Gemini API error generating lyrics: {e} | Raw: {raw_error}") from e
        except Exception as e:
            raw_error = str(e)
            if hasattr(e, "response"):
                raw_error = f"Response: {getattr(e.response, 'text', raw_error)}"
            raise RuntimeError(f"Gemini API error generating lyrics: {e} | Raw: {raw_error}") from e

    def generate_youtube_metadata(
        self, theme: str, track_count: int
    ) -> dict[str, Any]:
        """
        Generate YouTube video metadata (title, description, tags).

        Args:
            theme: Project theme
            track_count: Number of tracks

        Returns:
            Dict with keys: 'title', 'description', 'tags' (list)

        Raises:
            Exception: If API call fails or response is invalid
        """
        prompt = f"""Generate YouTube video metadata for a music compilation.

Theme: {theme}
Number of tracks: {track_count}

Generate:
1. A compelling title (under 100 characters)
2. A description (include placeholder for chapters: "Chapters:\\n00:00 Track 1\\n...")
3. Relevant tags (array of strings, 5-10 tags)

Return JSON: {{"title": "...", "description": "...", "tags": [...]}}
Make sure the JSON is valid and parseable."""

        try:
            # Wrap API call with retry logic
            response = retry_call(
                lambda: self.client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                ),
                max_retries=3,
                initial_delay=1.0,
            )

            response_text = response.text.strip()

            # Try to extract JSON from markdown code blocks if present
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()

            # Parse JSON
            metadata = json.loads(response_text)

            if not isinstance(metadata, dict):
                raise ValueError(f"Expected dict, got {type(metadata)}")

            # Validate required fields
            if "title" not in metadata or "description" not in metadata:
                raise ValueError(f"Missing required fields in metadata: {metadata}")

            title = str(metadata["title"]).strip()
            description = str(metadata["description"]).strip()
            tags = metadata.get("tags", [])

            if not isinstance(tags, list):
                tags = []

            # Validate title length
            if len(title) > 100:
                raise ValueError(f"Title too long: {len(title)} characters, max 100")

            if not title:
                raise ValueError("Title is empty")

            if not description:
                raise ValueError("Description is empty")

            return {
                "title": title,
                "description": description,
                "tags": [str(tag).strip() for tag in tags if tag],
            }

        except json.JSONDecodeError as e:
            raise ValueError(
                f"Failed to parse JSON response: {e}\nResponse: {response_text}"
            ) from e
        except google_exceptions.GoogleAPIError as e:
            raw_error = f"Google API error: {str(e)}"
            if hasattr(e, "status_code"):
                raw_error = f"HTTP {e.status_code}: {raw_error}"
            raise RuntimeError(f"Gemini API error: {e} | Raw: {raw_error}") from e
        except Exception as e:
            raw_error = str(e)
            if hasattr(e, "response"):
                raw_error = f"Response: {getattr(e.response, 'text', raw_error)}"
            raise RuntimeError(f"Gemini API error: {e} | Raw: {raw_error}") from e

    def generate_background_image(self, theme: str, output_path: str) -> None:
        """
        Generate a background image using Gemini 2.5 Flash Image API.

        Args:
            theme: Project theme to generate image for
            output_path: Path where to save the generated image

        Raises:
            Exception: If API call fails or image cannot be saved
        """
        from pathlib import Path
        from google.genai import types

        # Create prompt for scenic background image
        prompt = (
            f"A beautiful, cinematic background scene matching the theme: {theme}. "
            f"Scenic and atmospheric, detailed background scenery, "
            f"cinematic composition, 16:9 aspect ratio, high quality, "
            f"perfect for a music video background. No text, no people in foreground, "
            f"focus on the environment and atmosphere."
        )

        try:
            # Generate image using gemini-2.5-flash-image model with retry
            response = retry_call(
                lambda: self.client.models.generate_content(
                    model="gemini-2.5-flash-image",
                    contents=[prompt],
                    config=types.GenerateContentConfig(
                        response_modalities=["IMAGE"],
                        image_config=types.ImageConfig(
                            aspect_ratio="16:9",
                        )
                    ),
                ),
                max_retries=3,
                initial_delay=1.0,
            )

            # Extract image from response
            image_saved = False
            for part in response.parts:
                if part.text is not None:
                    # Log any text response (descriptions, etc.)
                    log_text = str(part.text)[:200]  # First 200 chars
                    if log_text:
                        pass  # Could log this if needed
                elif part.inline_data is not None:
                    # Save image
                    image = part.as_image()
                    output_file = Path(output_path)
                    output_file.parent.mkdir(parents=True, exist_ok=True)
                    image.save(str(output_file))
                    image_saved = True
                    break

            if not image_saved:
                raise RuntimeError("No image data found in Gemini response")

            if not Path(output_path).exists():
                raise RuntimeError(f"Image was not saved to {output_path}")

        except google_exceptions.GoogleAPIError as e:
            raw_error = f"Google API error: {str(e)}"
            if hasattr(e, "status_code"):
                raw_error = f"HTTP {e.status_code}: {raw_error}"
            raise RuntimeError(f"Gemini API error generating background image: {e} | Raw: {raw_error}") from e
        except Exception as e:
            raw_error = str(e)
            if hasattr(e, "response"):
                raw_error = f"Response: {getattr(e.response, 'text', raw_error)}"
            raise RuntimeError(f"Gemini API error generating background image: {e} | Raw: {raw_error}") from e

