# Brand assets for cafe_jazz channel

This folder contains channel-specific brand assets that override defaults.

## Files

- `background.png` (optional): Channel-specific background image (1920x1080 recommended)
  - If present, this will be used instead of generating a new background
  - Falls back to project-specific `assets/background.png` if not present
  - Falls back to Gemini-generated background if neither exists

- `font.ttf` or `font.otf` (optional): Custom font file for thumbnails
  - If present, this font will be used for all text overlays in thumbnails
  - Falls back to Cinzel (if available) or system serif fonts

- `thumbnail_template.png` (optional, future use): Base template for thumbnails

## Usage

The render step automatically checks this folder when processing projects for the `cafe_jazz` channel.

Example structure:
```
assets/brand/cafe_jazz/
  background.png
  font.ttf
  README.md
```

