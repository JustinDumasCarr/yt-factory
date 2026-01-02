# Task: Create Pixabay Audio API provider

**Task ID:** 86c7atbwu  
**Status:** IN PROGRESS  
**URL:** https://app.clickup.com/t/86c7atbwu

## Goal

Implement Pixabay Audio API client to search and download royalty-free ambient sounds as a fallback source.

## Scope

**IN:**
- Create `src/ytf/providers/pixabay.py` with API client
- Implement search by keywords
- Implement download with license metadata (all Pixabay audio is free for commercial use)
- Store `PIXABAY_API_KEY` in `.env` (document setup)

**OUT:**
- No CLI integration yet (separate task)
- No soundbank module integration yet (separate task)

## Acceptance Criteria

- `PixabayProvider` class with `search()` and `download()` methods
- Search returns audio results with metadata
- Download extracts audio file and sets license to "Pixabay"
- API key loaded from environment variable
- Error handling for API failures

## Verify Commands

```bash
# Verify provider compiles
python3 -m compileall -q src/ytf/providers/pixabay.py

# Test search (requires API key)
python3 -c "from ytf.providers.pixabay import PixabayProvider; p = PixabayProvider(); results = p.search('ocean waves', limit=3); print(f'Found {len(results)} results')"

# Verify license is set
python3 -c "from ytf.providers.pixabay import PixabayProvider; p = PixabayProvider(); results = p.search('rain', limit=1); assert results[0].get('license') == 'Pixabay' if results else True; print('✓ License set correctly')"
```
