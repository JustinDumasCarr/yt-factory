# Soundbank Providers

The soundbank system supports multiple sources for downloading or generating ambient sounds for the tinnitus channel. Sources are tried in priority order with automatic fallback.

## Supported Sources

1. **Freesound** (primary) - Creative Commons sounds (CC0, CC-BY)
2. **Pixabay** (fallback) - Royalty-free sounds
3. **Suno** (tertiary) - AI-generated ambient sounds

## API Key Setup

### Freesound API Key

1. Register for a free account at https://freesound.org/
2. Apply for API access at https://freesound.org/apiv2/apply/
3. Once approved, get your API key from your account settings
4. Add to `.env`:
   ```
   FREESOUND_API_KEY=your_api_key_here
   ```

**Note**: Freesound API access requires approval (usually granted within 24-48 hours for free accounts).

### Pixabay API Key

1. Register for a free account at https://pixabay.com/
2. Get your API key from https://pixabay.com/api/docs/
3. Add to `.env`:
   ```
   PIXABAY_API_KEY=your_api_key_here
   ```

**Note**: Pixabay API is free and requires no approval.

### Suno API Key

Suno API key setup is documented in `docs/06_PROVIDERS_SUNO.md`. Add to `.env`:
```
SUNO_API_KEY=your_api_key_here
```

## License Types and Commercial Use

The soundbank tracks license metadata for each sound to ensure commercial use compliance:

### CC0 (Creative Commons Zero)
- **Commercial use**: ✅ Allowed
- **Attribution**: Not required
- **Source**: Freesound
- **Description**: Public domain, no restrictions

### CC-BY (Creative Commons Attribution)
- **Commercial use**: ✅ Allowed
- **Attribution**: Required (credit the creator)
- **Source**: Freesound
- **Description**: Free to use commercially with attribution

### Pixabay
- **Commercial use**: ✅ Allowed
- **Attribution**: Not required (but appreciated)
- **Source**: Pixabay
- **Description**: Free for commercial use under Pixabay License

### Suno
- **Commercial use**: ✅ Allowed (per Suno terms)
- **Attribution**: Not required
- **Source**: Suno
- **Description**: Generated content, commercial use allowed per Suno API terms

### Manual
- **Commercial use**: ✅ Assumed (user-provided)
- **Attribution**: Depends on source
- **Source**: User upload
- **Description**: User-provided files, assume user has rights

## Usage

### Search Sounds

Search across Freesound and Pixabay:
```bash
ytf soundbank search "cicadas"
```

### Generate/Download with Auto-Fallback

Automatically tries sources in priority order:
```bash
ytf soundbank generate cicadas_001 --query "cicadas" --name "Cicadas"
```

### Specify Source

Force a specific source:
```bash
# Freesound only
ytf soundbank generate cicadas_001 --query "cicadas" --source freesound

# Pixabay only
ytf soundbank generate ocean_001 --query "ocean waves" --source pixabay

# Suno only
ytf soundbank generate rain_001 --query "gentle rain" --source suno --style "Ambient"
```

### Direct Download

Download a specific sound by ID:
```bash
# Freesound
ytf soundbank download freesound 12345 --id cicadas_001 --name "Cicadas"

# Pixabay (requires download URL from search)
ytf soundbank download pixabay "https://..." --id ocean_001 --name "Ocean Waves"
```

## Troubleshooting

### "FREESOUND_API_KEY environment variable is not set"
- Add `FREESOUND_API_KEY` to your `.env` file
- Ensure you've applied for and received API access from Freesound

### "PIXABAY_API_KEY environment variable is not set"
- Add `PIXABAY_API_KEY` to your `.env` file
- Get your API key from https://pixabay.com/api/docs/

### "No Freesound results found"
- Check that your API key is valid
- Verify the search query (try simpler terms)
- Freesound only returns CC0 and CC-BY licensed sounds (commercial use allowed)

### "No Pixabay results found"
- Check that your API key is valid
- Verify the search query
- Pixabay may have fewer audio files than images

### Suno generates songs instead of ambient sounds
- Suno's `instrumental=True` mode ignores the `prompt` parameter
- The system uses `negativeTags` to exclude musical elements
- Try using style "Ambient", "Nature Sounds", or "White Noise"
- If results are still too musical, prefer Freesound or Pixabay for ambient sounds

### "All sound sources failed"
- Check that at least one API key is set
- Verify network connectivity
- Check API key validity
- Review error messages for specific failures

## License Compliance

All sounds in the soundbank are tracked with license metadata:
- `license_type`: The license type (CC0, CC-BY, Pixabay, Suno, manual, custom)
- `license_url`: URL to license documentation (if available)
- `commercial_ok`: Boolean flag indicating commercial use is allowed

**Important**: Only sounds with `commercial_ok=True` should be used in commercial projects. The system automatically filters Freesound results to only CC0 and CC-BY licenses (both allow commercial use).

## Best Practices

1. **Prefer Freesound/Pixabay for ambient sounds**: These sources provide actual field recordings and nature sounds, not AI-generated music
2. **Use Suno as fallback**: Suno is better for generating music, but can work for ambient with proper style/tags
3. **Check license before use**: Always verify `commercial_ok=True` before using sounds in commercial projects
4. **Attribution for CC-BY**: If using CC-BY licensed sounds, ensure proper attribution in video descriptions
