# Gemini provider

Gemini is used for planning, optional lyrics, and background image generation.

## Inputs
- theme
- vocals on/off
- target_minutes
- track_count

## Outputs
- List of track prompts that stay consistent with the theme.
- Optional lyrics per track when vocals enabled.
- YouTube metadata draft.
- Background images (requires paid API plan - see below).

## API Plan Requirements

**IMPORTANT**: Background image generation requires a **PAID Gemini API plan**.
- The free tier does NOT include access to `gemini-2.5-flash-image` model
- Text generation (planning, lyrics) works on the free tier
- Image generation will fail with 429 errors on free tier
- Upgrade at: https://ai.google.dev/pricing

## Prompt strategy
Use a strict template:
- theme descriptor
- mood tags
- instrumentation tags
- tempo guidance
- constraints: "no artist references", "no copyrighted lyrics", "no brand names"

Variation control:
- tight variations only
- re-use a small set of motifs across tracks for coherence

## Lyrics rules
When vocals enabled:
- generate original lyrics
- no references to real artists
- no quotes from existing songs
- avoid brand names
- keep chorus structure simple for listenability
