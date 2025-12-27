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
- Upload is idempotent for the video upload itself:
  - If `project.json.youtube.video_id` exists and `project.json.youtube.thumbnail_uploaded==true`, upload step skips.
  - If `project.json.youtube.video_id` exists but thumbnail is not uploaded yet, upload step will retry **thumbnail upload** (it will not skip).

## Metadata
- title (from plan step)
- description (from `output/youtube_description.txt` if available, else from plan metadata)
- tags (from plan step, validated against channel tag rules)
- category (from channel profile `upload_defaults.category_id`)
- default language (from channel profile `upload_defaults.default_language`)
- made for kids (from channel profile `upload_defaults.made_for_kids`)

## Thumbnail upload
- **Required**: Upload will not proceed unless a thumbnail exists on disk.
  - `project.render.thumbnail_path` must be set
  - the file must exist at `projects/<id>/<thumbnail_path>`
- Thumbnail upload failure **fails the step** (so you can retry later).
- Thumbnail upload status is persisted in `project.json.youtube.thumbnail_uploaded` and `thumbnail_path`.

## Reliability
- Use resumable uploads with exponential backoff retry (max 10 retries).
- Write progress logs to `logs/upload.log`.
- On failure, keep the mp4 and retry upload only (re-run `ytf upload <id>`).
- Raw HTTP error content is logged for debugging.

## Re-run behavior
- If video already uploaded (`project.json.youtube.video_id` exists):
  - If thumbnail not uploaded yet, upload step attempts thumbnail upload and then completes.
  - If thumbnail already uploaded, upload step skips and logs the existing video URL.
  - To re-upload the video, manually clear `project.json.youtube.video_id` first.
