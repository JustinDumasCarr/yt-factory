"""
Freesound provider: searches and downloads Creative Commons ambient sounds.

Uses Freesound API v2 to search for sounds by keywords and download audio files.
Filters by commercial-use licenses (CC0, CC-BY) only.
"""

import os
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv

from ytf.utils.retry import retry_call

# Load environment variables from .env file
load_dotenv()

BASE_URL = "https://freesound.org/apiv2"


class FreesoundProvider:
    """Wrapper for Freesound API calls."""

    def __init__(self):
        """
        Initialize Freesound client.

        Raises:
            ValueError: If FREESOUND_API_KEY is not set
        """
        api_key = os.getenv("FREESOUND_API_KEY")
        if not api_key:
            raise ValueError(
                "FREESOUND_API_KEY environment variable is not set. "
                "Please set it in your .env file. Get your API key at: "
                "https://freesound.org/apiv2/apply/"
            )
        self.api_key = api_key
        self.client = httpx.Client(
            base_url=BASE_URL,
            headers={"Authorization": f"Token {self.api_key}"},
            timeout=30.0,
        )

    def search(
        self, query: str, limit: int = 10, filter_license: bool = True
    ) -> list[dict[str, Any]]:
        """
        Search for sounds on Freesound.

        Args:
            query: Search query (keywords, tags, etc.)
            limit: Maximum number of results to return (default 10)
            filter_license: If True, only return CC0 and CC-BY licensed sounds (default True)

        Returns:
            List of sound result dicts with keys: id, name, license, url, previews, etc.

        Raises:
            RuntimeError: If API call fails
        """
        # Note: Freesound API doesn't support filtering by license directly in the filter parameter
        # We'll filter results after fetching (license field is always returned in default fields)

        params = {
            "query": query,
            "page_size": (
                min(limit * 2, 150) if filter_license else min(limit, 150)
            ),  # Fetch more if filtering
            "fields": "id,name,license,url,previews,duration,username,tags,description",
        }

        try:
            # Wrap API call with retry logic
            response = retry_call(
                lambda: self.client.get("/search/", params=params),
                max_retries=3,
                initial_delay=1.0,
            )
            response.raise_for_status()

            data = response.json()

            results = data.get("results", [])

            # Normalize license values to our format and filter
            normalized_results = []
            for result in results:
                if len(normalized_results) >= limit:
                    break

                license_value = result.get("license", "")
                # Map Freesound license values to our format
                # Freesound uses: "Creative Commons 0" for CC0, "Attribution" for CC-BY
                license_type = None
                if license_value == "Creative Commons 0":
                    license_type = "CC0"
                elif license_value == "Attribution":
                    license_type = "CC-BY"

                # Filter by license if requested
                if filter_license and not license_type:
                    continue  # Skip non-commercial licenses

                # Include result (with or without license based on filter_license)
                normalized_result = {
                    "id": result.get("id"),
                    "name": result.get("name"),
                    "license": license_type,
                    "license_url": (
                        "https://freesound.org/help/licenses/" if license_type else None
                    ),
                    "url": result.get("url"),
                    "previews": result.get("previews", {}),
                    "duration": result.get("duration", 0),
                    "username": result.get("username"),
                    "tags": result.get("tags", []),
                    "description": result.get("description", ""),
                }
                normalized_results.append(normalized_result)

            return normalized_results

        except httpx.HTTPStatusError as e:
            raw_error = f"HTTP {e.response.status_code}: {e.response.text[:500]}"
            raise RuntimeError(
                f"Freesound API HTTP error: {e.response.status_code} - {e.response.text} | Raw: {raw_error}"
            ) from e
        except Exception as e:
            raw_error = str(e)
            if hasattr(e, "response") and hasattr(e.response, "text"):
                raw_error = f"Response: {e.response.text[:500]}"
            raise RuntimeError(f"Freesound API error: {e} | Raw: {raw_error}") from e

    def download(self, sound_id: int, output_path: str) -> dict[str, Any]:
        """
        Download a sound file from Freesound.

        Args:
            sound_id: Freesound sound ID
            output_path: Local path to save the audio file

        Returns:
            Dict with sound metadata including license info

        Raises:
            RuntimeError: If download fails
            FileNotFoundError: If sound doesn't exist
        """
        # First get sound details to check license
        try:
            detail_response = retry_call(
                lambda: self.client.get(
                    f"/sounds/{sound_id}/", params={"fields": "id,name,license,url,previews"}
                ),
                max_retries=3,
                initial_delay=1.0,
            )
            detail_response.raise_for_status()
            sound_data = detail_response.json()

            license_value = sound_data.get("license", "")
            license_type = None
            if license_value == "Creative Commons 0":
                license_type = "CC0"
            elif license_value == "Attribution":
                license_type = "CC-BY"

            if not license_type:
                raise ValueError(
                    f"Sound {sound_id} does not have a commercial-use license. "
                    f"License: {license_value}"
                )
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise FileNotFoundError(f"Sound {sound_id} not found on Freesound") from e
            raise RuntimeError(f"Failed to get sound details: {e}") from e

        # Download the audio file
        try:
            # Ensure output directory exists
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)

            # Download using the download endpoint
            download_response = retry_call(
                lambda: self.client.get(f"/sounds/{sound_id}/download/", follow_redirects=True),
                max_retries=3,
                initial_delay=1.0,
            )
            download_response.raise_for_status()

            # Write file
            with open(output_path, "wb") as f:
                f.write(download_response.content)

            # Return metadata
            return {
                "id": sound_data.get("id"),
                "name": sound_data.get("name"),
                "license": license_type,
                "license_url": "https://freesound.org/help/licenses/",
                "url": sound_data.get("url"),
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
