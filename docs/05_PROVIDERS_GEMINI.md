# Gemini provider

Gemini is used for planning and optional lyrics.

## Inputs
- theme
- vocals on/off
- target_minutes
- track_count

## Outputs
- List of track prompts that stay consistent with the theme.
- Optional lyrics per track when vocals enabled.
- YouTube metadata draft.

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
