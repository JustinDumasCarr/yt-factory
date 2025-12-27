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
        self, theme: str, track_count: int, vocals_enabled: bool
    ) -> list[dict[str, str]]:
        """
        Generate track data (style, title, prompt) for all tracks in one API call.

        Args:
            theme: Project theme
            track_count: Number of tracks to generate
            vocals_enabled: Whether tracks should include vocals

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
- NO brand names

Return JSON array: [{{"style": "...", "title": "...", "prompt": "..."}}, ...]
Make sure the JSON is valid and parseable."""

        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
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
        except Exception as e:
            raise RuntimeError(f"Gemini API error: {e}") from e

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
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
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

        except Exception as e:
            raise RuntimeError(f"Gemini API error generating lyrics: {e}") from e

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
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
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
        except Exception as e:
            raise RuntimeError(f"Gemini API error: {e}") from e

