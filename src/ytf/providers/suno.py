"""
Suno provider: generates music tracks via Suno API.

Uses httpx for HTTP calls. Implements poll-only strategy (no callback server).
All API calls follow the official Suno API documentation.
"""

import json
import os
import time
from typing import Any, Optional

import httpx

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

BASE_URL = "https://api.sunoapi.org"


class SunoProvider:
    """Wrapper for Suno API calls."""

    def __init__(self):
        """
        Initialize Suno client.

        Raises:
            ValueError: If SUNO_API_KEY is not set
        """
        api_key = os.getenv("SUNO_API_KEY")
        if not api_key:
            raise ValueError(
                "SUNO_API_KEY environment variable is not set. "
                "Please set it in your .env file."
            )
        self.api_key = api_key
        self.model = os.getenv("SUNO_MODEL", "V4_5ALL")
        self.callback_url = os.getenv(
            "SUNO_CALLBACK_URL", "http://localhost/ytf-suno-callback-disabled"
        )
        self.client = httpx.Client(
            base_url=BASE_URL,
            headers={"Authorization": f"Bearer {self.api_key}"},
            timeout=30.0,
        )

    def generate_music(
        self,
        style: str,
        title: str,
        prompt: Optional[str] = None,
        instrumental: bool = False,
    ) -> str:
        """
        Submit a music generation job to Suno.

        Args:
            style: Music style/genre (required for customMode)
            title: Track title (required for customMode)
            prompt: Lyrics text (required if instrumental=False, used as exact lyrics)
            instrumental: Whether track should be instrumental

        Returns:
            Task ID string

        Raises:
            RuntimeError: If API call fails
        """
        payload = {
            "customMode": True,
            "instrumental": instrumental,
            "model": self.model,
            "callBackUrl": self.callback_url,
            "style": style,
            "title": title,
        }

        # In customMode, prompt is required if instrumental=false
        if not instrumental:
            if not prompt:
                raise ValueError(
                    "prompt (lyrics) is required when instrumental=false in customMode"
                )
            payload["prompt"] = prompt
        # If instrumental=true, prompt is not used (per Suno docs)

        try:
            response = self.client.post("/api/v1/generate", json=payload)
            response.raise_for_status()

            data = response.json()

            if data.get("code") != 200:
                raise RuntimeError(
                    f"Suno API error: code={data.get('code')}, msg={data.get('msg')}"
                )

            task_id = data.get("data", {}).get("taskId")
            if not task_id:
                raise RuntimeError(
                    f"Suno API response missing taskId: {json.dumps(data)}"
                )

            return task_id

        except httpx.HTTPStatusError as e:
            raise RuntimeError(
                f"Suno API HTTP error: {e.response.status_code} - {e.response.text}"
            ) from e
        except Exception as e:
            raise RuntimeError(f"Suno API error: {e}") from e

    def get_generation_status(self, task_id: str) -> dict[str, Any]:
        """
        Poll for music generation status and results.

        Args:
            task_id: Task ID from generate_music()

        Returns:
            Dict with status information:
            - "status": "pending" | "complete" | "failed"
            - "sunoData": list of track data (when complete)
            - "raw": full API response

        Raises:
            RuntimeError: If API call fails
        """
        try:
            response = self.client.get(
                "/api/v1/generate/record-info", params={"taskId": task_id}
            )
            response.raise_for_status()

            data = response.json()

            if data.get("code") != 200:
                return {
                    "status": "failed",
                    "sunoData": [],
                    "raw": json.dumps(data),
                    "error": data.get("msg", "Unknown error"),
                }

            # Check if generation is complete
            response_data = data.get("data", {}).get("response", {})
            suno_data = response_data.get("sunoData", [])

            if suno_data and len(suno_data) > 0:
                # Check if we have at least one track with audioUrl
                has_audio = any(
                    track.get("audioUrl") for track in suno_data if isinstance(track, dict)
                )
                if has_audio:
                    return {
                        "status": "complete",
                        "sunoData": suno_data,
                        "raw": json.dumps(data),
                    }

            # Still processing
            return {
                "status": "pending",
                "sunoData": [],
                "raw": json.dumps(data),
            }

        except httpx.HTTPStatusError as e:
            raise RuntimeError(
                f"Suno API HTTP error: {e.response.status_code} - {e.response.text}"
            ) from e
        except Exception as e:
            raise RuntimeError(f"Suno API error: {e}") from e

    def poll_until_complete(
        self, task_id: str, max_wait_minutes: int = 20, initial_delay: int = 5
    ) -> dict[str, Any]:
        """
        Poll for generation completion with exponential backoff.

        Args:
            task_id: Task ID to poll
            max_wait_minutes: Maximum time to wait (default 20 minutes)
            initial_delay: Initial delay between polls in seconds (default 5)

        Returns:
            Status dict from get_generation_status() when complete or failed

        Raises:
            TimeoutError: If max_wait_minutes exceeded
        """
        max_wait_seconds = max_wait_minutes * 60
        start_time = time.time()
        delay = initial_delay
        max_delay = 30  # Cap at 30 seconds

        while True:
            status_info = self.get_generation_status(task_id)

            if status_info["status"] == "complete":
                return status_info
            if status_info["status"] == "failed":
                return status_info

            # Check timeout
            elapsed = time.time() - start_time
            if elapsed >= max_wait_seconds:
                raise TimeoutError(
                    f"Generation timeout after {max_wait_minutes} minutes for task {task_id}"
                )

            # Exponential backoff with cap
            time.sleep(delay)
            delay = min(delay * 1.5, max_delay)

    def download_audio(self, audio_url: str, output_path: str) -> None:
        """
        Download audio file from Suno URL.

        Args:
            audio_url: URL to audio file
            output_path: Local path to save file

        Raises:
            RuntimeError: If download fails
        """
        try:
            response = self.client.get(audio_url, follow_redirects=True)
            response.raise_for_status()

            # Ensure output directory exists
            from pathlib import Path

            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)

            # Write file
            with open(output_path, "wb") as f:
                f.write(response.content)

        except httpx.HTTPStatusError as e:
            raise RuntimeError(
                f"Download HTTP error: {e.response.status_code} - {e.response.text}"
            ) from e
        except Exception as e:
            raise RuntimeError(f"Download error: {e}") from e

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

