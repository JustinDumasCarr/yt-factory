# YouTube upload

Uploads use the official YouTube Data API with OAuth.

## Local OAuth setup
- Create OAuth client credentials in Google Cloud Console.
- Store client secrets locally.
- Cache OAuth tokens locally so you only authorize once.

## Upload behavior (default)
- Upload as Unlisted.
- Save returned video ID in project.json.

## Metadata
- title
- description
- tags
- category (optional)
- chapters in description if supported by format

## Reliability
- Use resumable uploads.
- Write progress logs to logs/upload.log.
- On failure, keep the mp4 and retry upload only.
