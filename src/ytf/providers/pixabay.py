"""
Pixabay provider: searches and downloads royalty-free audio files.

Uses Pixabay API to search for audio files by keywords and download them.
All Pixabay audio is free for commercial use (Pixabay License).
"""

import os
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv

from ytf.utils.retry import retry_call

# Load environment variables from .env file
load_dotenv()

BASE_URL = "https://pixabay.com/api"


class PixabayProvider:
    """Wrapper for Pixabay API calls."""

    def __init__(self):
        """
        Initialize Pixabay client.

        Raises:
            ValueError: If PIXABAY_API_KEY is not set
        """
        api_key = os.getenv("PIXABAY_API_KEY")
        if not api_key:
            raise ValueError(
                "PIXABAY_API_KEY environment variable is not set. "
                "Please set it in your .env file. Get your API key at: "
                "https://pixabay.com/api/docs/"
            )
        self.api_key = api_key
        self.client = httpx.Client(
            base_url=BASE_URL,
            timeout=30.0,
        )

    def search(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """
        Search for audio files on Pixabay.

        Args:
            query: Search query (keywords)
            limit: Maximum number of results to return (default 10, max 200)

        Returns:
            List of audio result dicts with keys: id, title, url, duration, etc.

        Raises:
            RuntimeError: If API call fails
        """
        params = {
            "key": self.api_key,
            "q": query,
            "audio_type": "all",  # Search all audio types (music, sound effects, etc.)
            "per_page": min(limit, 200),  # Pixabay max is 200 per page
            "safesearch": "true",  # Enable safe search
        }

        try:
            # Wrap API call with retry logic
            response = retry_call(
                lambda: self.client.get("/", params=params),
                max_retries=3,
                initial_delay=1.0,
            )
            response.raise_for_status()

            data = response.json()

            # Pixabay returns hits array
            hits = data.get("hits", [])

            # Normalize results to our format
            normalized_results = []
            for hit in hits[:limit]:
                # Pixabay audio fields structure (similar to video API)
                # Audio may have: id, title, url (download URL), duration, etc.
                # Note: Pixabay audio API structure may vary - adjust based on actual response
                normalized_result = {
                    "id": hit.get("id"),
                    "title": hit.get("title", hit.get("name", "")),
                    "name": hit.get("title", hit.get("name", "")),  # Alias for consistency
                    "license": "Pixabay",  # All Pixabay content is free for commercial use
                    "license_url": "https://pixabay.com/service/license/",
                    "url": hit.get("pageURL", ""),  # Page URL
                    "download_url": hit.get("url")
                    or hit.get("audio_url")
                    or hit.get("download"),  # Direct download URL (field name may vary)
                    "duration": hit.get("duration", 0),  # Duration in seconds
                    "tags": (
                        hit.get("tags", "").split(", ")
                        if isinstance(hit.get("tags"), str)
                        else (hit.get("tags", []) if isinstance(hit.get("tags"), list) else [])
                    ),
                    "user": hit.get("user", ""),
                }
                normalized_results.append(normalized_result)

            return normalized_results

        except httpx.HTTPStatusError as e:
            raw_error = f"HTTP {e.response.status_code}: {e.response.text[:500]}"
            raise RuntimeError(
                f"Pixabay API HTTP error: {e.response.status_code} - {e.response.text} | Raw: {raw_error}"
            ) from e
        except Exception as e:
            raw_error = str(e)
            if hasattr(e, "response") and hasattr(e.response, "text"):
                raw_error = f"Response: {e.response.text[:500]}"
            raise RuntimeError(f"Pixabay API error: {e} | Raw: {raw_error}") from e

    def download(self, audio_id: int, output_path: str) -> dict[str, Any]:
        """
        Download an audio file from Pixabay.

        Args:
            audio_id: Pixabay audio ID
            output_path: Local path to save the audio file

        Returns:
            Dict with audio metadata including license info

        Raises:
            RuntimeError: If download fails
            FileNotFoundError: If audio doesn't exist
        """
        # First get audio details via search (Pixabay doesn't have a direct get-by-id endpoint)
        # We'll search for the ID and get the download URL
        try:
            # Search for the specific audio by ID (this is a workaround - Pixabay doesn't have direct ID lookup)
            # We'll need to get the download URL from a previous search result
            # For now, we'll require the download_url to be passed or fetched from search results
            raise NotImplementedError(
                "Pixabay download requires download_url from search results. "
                "Use search() first to get the download_url, then call download_with_url()."
            )
        except Exception as e:
            raise RuntimeError(f"Failed to download audio {audio_id}: {e}") from e

    def download_with_url(self, download_url: str, output_path: str) -> dict[str, Any]:
        """
        Download an audio file from Pixabay using a direct download URL.

        Args:
            download_url: Direct download URL from search results
            output_path: Local path to save the audio file

        Returns:
            Dict with audio metadata

        Raises:
            RuntimeError: If download fails
        """
        try:
            # Ensure output directory exists
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)

            # Download the audio file
            download_response = retry_call(
                lambda: self.client.get(download_url, follow_redirects=True),
                max_retries=3,
                initial_delay=1.0,
            )
            download_response.raise_for_status()

            # Write file
            with open(output_path, "wb") as f:
                f.write(download_response.content)

            # Return metadata
            return {
                "license": "Pixabay",
                "license_url": "https://pixabay.com/service/license/",
                "commercial_ok": True,
            }

        except httpx.HTTPStatusError as e:
            raw_error = f"HTTP {e.response.status_code}: {e.response.text[:500]}"
            raise RuntimeError(
                f"Download HTTP error: {e.response.status_code} - {e.response.text} | Raw: {raw_error}"
            ) from e
        except Exception as e:
            raw_error = str(e)
            if hasattr(e, "response") and hasattr(e.response, "text"):
                raw_error = f"Response: {e.response.text[:500]}"
            raise RuntimeError(f"Download error: {e} | Raw: {raw_error}") from e

    def close(self):
        """Close HTTP client explicitly."""
        if hasattr(self, "client"):
            self.client.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - close client."""
        self.close()
        return False
