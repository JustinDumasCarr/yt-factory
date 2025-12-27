# Brand assets for cafe_jazz channel

This folder contains channel-specific brand assets for styling.

## Files

- `font.ttf` or `font.otf` (optional): Custom font file for thumbnails
  - If present, this font will be used for all text overlays in thumbnails
  - Falls back to Cinzel (if available) or system serif fonts

- `thumbnail_template.png` (optional, future use): Base template for thumbnails

## Background Images

**Note**: Background images are **not** stored in brand folders. Each project generates its own unique background image at `projects/<project_id>/assets/background.png` using Gemini with channel-aware prompts. This ensures every YouTube video has a unique, project-specific background.

## Usage

The render step automatically checks this folder when processing projects for the `cafe_jazz` channel to find custom fonts.

Example structure:
```
assets/brand/cafe_jazz/
  font.ttf
  README.md
```

