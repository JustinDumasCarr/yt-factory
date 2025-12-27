# YouTube upload

Uploads use the official YouTube Data API with OAuth.

## Local OAuth setup
- Create OAuth client credentials in Google Cloud Console.
- Store client secrets locally in a file (e.g., `credentials.json`).
- Set `YOUTUBE_OAUTH_CREDENTIALS_PATH` in `.env` to point to the credentials file.
- Cache OAuth tokens locally at `projects/<id>/.youtube_token.json` so you only authorize once per project.

## Required environment variables
- `YOUTUBE_OAUTH_CREDENTIALS_PATH`: Path to OAuth client secrets JSON file

## Upload behavior (channel-driven)
- Privacy, category, language, and made-for-kids settings come from channel profile.
- Default: Unlisted, Category 10 (Music), English, not made for kids.
- Upload is idempotent: if `project.json.youtube.video_id` exists, upload step skips (logs warning).

## Metadata
- title (from plan step)
- description (from `output/youtube_description.txt` if available, else from plan metadata)
- tags (from plan step, validated against channel tag rules)
- category (from channel profile `upload_defaults.category_id`)
- default language (from channel profile `upload_defaults.default_language`)
- made for kids (from channel profile `upload_defaults.made_for_kids`)

## Thumbnail upload
- Automatically uploads thumbnail if `project.render.thumbnail_path` exists and file is present.
- Thumbnail upload failure is logged as warning but does not fail the step.
- Thumbnail upload status is persisted in `project.json.youtube.thumbnail_uploaded` and `thumbnail_path`.

## Reliability
- Use resumable uploads with exponential backoff retry (max 10 retries).
- Write progress logs to `logs/upload.log`.
- On failure, keep the mp4 and retry upload only (re-run `ytf upload <id>`).
- Raw HTTP error content is logged for debugging.

## Re-run behavior
- If video already uploaded (`project.json.youtube.video_id` exists):
  - Upload step skips and logs a warning with the existing video URL.
  - To re-upload, manually clear `project.json.youtube.video_id` first.
