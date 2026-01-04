# Verification

## Running Verification

Execute verification using:

```bash
./scripts/verify.sh
```

Or:

```bash
bash scripts/verify.sh
```

## What It Does

The verify script runs a series of offline checks to ensure:
- Code is syntactically valid
- The CLI can start (`--help`) without requiring API keys
- `project.json` schema validation works (Pydantic models)
- Unit tests pass (pytest)

## Notes

- Verification must **not** require Suno/Gemini/YouTube credentials.
- Verification must **avoid network calls** (no external API requests).
- CI should run the same entrypoint: `scripts/verify.sh`.

