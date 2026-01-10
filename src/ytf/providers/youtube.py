"""
YouTube provider: handles OAuth authentication and video uploads.

Uses YouTube Data API v3 with OAuth 2.0 authentication.
Implements token caching and resumable uploads.
"""

import json
import os
import time
from pathlib import Path

from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

from ytf.project import PROJECTS_DIR

# Load environment variables from .env file
load_dotenv()

# OAuth 2.0 scopes required for YouTube upload
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

# Retriable HTTP status codes for exponential backoff
RETRIABLE_STATUS_CODES = [429, 500, 502, 503, 504]

# Maximum number of retries
MAX_RETRIES = 10


class YouTubeProvider:
    """Wrapper for YouTube Data API v3 operations."""

    def __init__(self, project_id: str):
        """
        Initialize YouTube provider with OAuth authentication.

        Args:
            project_id: Project ID for token caching

        Raises:
            ValueError: If YOUTUBE_OAUTH_CREDENTIALS_PATH is not set
            FileNotFoundError: If credentials file doesn't exist
        """
        credentials_path = os.getenv("YOUTUBE_OAUTH_CREDENTIALS_PATH")
        if not credentials_path:
            raise ValueError(
                "YOUTUBE_OAUTH_CREDENTIALS_PATH environment variable is not set. "
                "Please set it in your .env file."
            )

        self.credentials_path = Path(credentials_path)
        if not self.credentials_path.exists():
            raise FileNotFoundError(f"YouTube OAuth credentials file not found: {credentials_path}")

        self.project_id = project_id
        self.token_path = PROJECTS_DIR / project_id / ".youtube_token.json"
        self.youtube = None
        self.credentials = None

    def _get_authenticated_service(self):
        """
        Get authenticated YouTube API service instance.

        Handles OAuth flow, token caching, and refresh.

        Returns:
            Authenticated YouTube API service object

        Raises:
            RuntimeError: If authentication fails
        """
        # If we already have a service, return it
        if self.youtube is not None:
            return self.youtube

        # Load or create credentials
        self.credentials = self._load_or_create_credentials()

        # Build and return YouTube service
        try:
            self.youtube = build("youtube", "v3", credentials=self.credentials)
            return self.youtube
        except Exception as e:
            raise RuntimeError(f"Failed to build YouTube API service: {e}") from e

    def _load_or_create_credentials(self) -> Credentials:
        """
        Load cached credentials or initiate OAuth flow.

        Returns:
            Valid Credentials object

        Raises:
            RuntimeError: If OAuth flow fails
        """
        # Try to load cached token
        if self.token_path.exists():
            try:
                with open(self.token_path, encoding="utf-8") as f:
                    token_data = json.load(f)
                credentials = Credentials.from_authorized_user_info(token_data, SCOPES)

                # Refresh if expired
                if credentials.expired and credentials.refresh_token:
                    credentials.refresh(Request())

                # Save refreshed token
                self._save_credentials(credentials)
                return credentials
            except Exception:
                # If loading fails, we'll create new credentials
                pass

        # No valid cached token, initiate OAuth flow
        try:
            flow = InstalledAppFlow.from_client_secrets_file(str(self.credentials_path), SCOPES)
            credentials = flow.run_local_server(port=0)
            self._save_credentials(credentials)
            return credentials
        except Exception as e:
            raise RuntimeError(
                f"OAuth authentication failed: {e}. "
                "Please ensure your credentials file is valid and you grant the required permissions."
            ) from e

    def _save_credentials(self, credentials: Credentials) -> None:
        """
        Save credentials to token cache file.

        Args:
            credentials: Credentials object to save
        """
        self.token_path.parent.mkdir(parents=True, exist_ok=True)
        token_data = {
            "token": credentials.token,
            "refresh_token": credentials.refresh_token,
            "token_uri": credentials.token_uri,
            "client_id": credentials.client_id,
            "client_secret": credentials.client_secret,
            "scopes": credentials.scopes,
        }
        with open(self.token_path, "w", encoding="utf-8") as f:
            json.dump(token_data, f, indent=2)

    def upload_video(
        self,
        video_path: Path,
        title: str,
        description: str,
        tags: list[str],
        privacy_status: str = "unlisted",
        category_id: str = "10",
        made_for_kids: bool = False,
        default_language: str = "en",
    ) -> dict:
        """
        Upload a video to YouTube using resumable upload protocol.

        Args:
            video_path: Path to video file to upload
            title: Video title
            description: Video description
            tags: List of tags
            privacy_status: Privacy status ("public", "private", "unlisted")
            category_id: YouTube category ID (default: "10" for Music)
            made_for_kids: Whether video is made for kids (default: False)
            default_language: Default language code (default: "en")

        Returns:
            Dictionary with video_id and other upload response data

        Raises:
            RuntimeError: If upload fails
            FileNotFoundError: If video file doesn't exist
        """
        if not video_path.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")

        youtube = self._get_authenticated_service()

        # Prepare metadata
        body = {
            "snippet": {
                "title": title,
                "description": description,
                "tags": tags,
                "categoryId": category_id,
                "defaultLanguage": default_language,
            },
            "status": {
                "privacyStatus": privacy_status,
                "selfDeclaredMadeForKids": made_for_kids,
            },
        }

        # Create media upload object
        media = MediaFileUpload(
            str(video_path),
            chunksize=2 * 1024 * 1024,  # 2MB chunks
            resumable=True,
            mimetype="video/mp4",
        )

        # Create insert request
        insert_request = youtube.videos().insert(
            part=",".join(body.keys()),
            body=body,
            media_body=media,
        )

        # Execute resumable upload with exponential backoff
        response = self._resumable_upload(insert_request)

        if "id" not in response:
            raise RuntimeError(f"Upload failed with unexpected response: {response}")

        return response

    def _resumable_upload(self, insert_request) -> dict:
        """
        Execute resumable upload with exponential backoff retry logic.

        Args:
            insert_request: YouTube API insert request object

        Returns:
            Upload response dictionary with video_id

        Raises:
            RuntimeError: If upload fails after all retries
        """
        response = None
        retry = 0

        while response is None:
            error = None
            try:
                status, response = insert_request.next_chunk()
                if response is not None:
                    if "id" in response:
                        return response
                    else:
                        raise RuntimeError(f"Upload failed with unexpected response: {response}")
            except HttpError as e:
                if e.resp.status in RETRIABLE_STATUS_CODES:
                    # Include raw error content in error message
                    raw_content = str(e.content)[:500] if e.content else "No content"
                    error = f"A retriable HTTP error {e.resp.status} occurred: {raw_content}"
                else:
                    # Non-retriable: include raw content in raised error
                    raw_content = str(e.content)[:500] if e.content else "No content"
                    raise RuntimeError(
                        f"Non-retriable HTTP error {e.resp.status} occurred | Raw: {raw_content}"
                    ) from e
            except Exception as e:
                raw_error = str(e)
                if hasattr(e, "response") and hasattr(e.response, "text"):
                    raw_error = f"Response: {e.response.text[:500]}"
                error = f"An unexpected error occurred: {e} | Raw: {raw_error}"

            if error is not None:
                if retry >= MAX_RETRIES:
                    raise RuntimeError(
                        f"Upload failed after {MAX_RETRIES} retries. Last error: {error}"
                    )

                retry += 1
                sleep_seconds = 2**retry  # Exponential backoff
                time.sleep(sleep_seconds)

        raise RuntimeError("Upload failed: no response received")

    def upload_thumbnail(self, video_id: str, thumbnail_path: Path) -> None:
        """
        Upload a custom thumbnail for a video.

        Args:
            video_id: YouTube video ID
            thumbnail_path: Path to thumbnail image file

        Raises:
            RuntimeError: If thumbnail upload fails
            FileNotFoundError: If thumbnail file doesn't exist
        """
        if not thumbnail_path.exists():
            raise FileNotFoundError(f"Thumbnail file not found: {thumbnail_path}")

        youtube = self._get_authenticated_service()

        try:
            youtube.thumbnails().set(
                videoId=video_id,
                media_body=MediaFileUpload(str(thumbnail_path)),
            ).execute()
        except HttpError as e:
            raw_content = str(e.content)[:500] if e.content else "No content"
            raise RuntimeError(
                f"Failed to upload thumbnail: HTTP {e.resp.status} | Raw: {raw_content}"
            ) from e
        except Exception as e:
            raw_error = str(e)
            if hasattr(e, "response") and hasattr(e.response, "text"):
                raw_error = f"Response: {e.response.text[:500]}"
            raise RuntimeError(f"Failed to upload thumbnail: {e} | Raw: {raw_error}") from e
