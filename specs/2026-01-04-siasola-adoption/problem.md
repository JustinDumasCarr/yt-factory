# Problem

## What problem are we solving?

The `yt-factory` repo needs to adopt the SIASOLA OS engineering contract to ensure agent work is verifiable and consistent across the codebase.

## Why is this important?

Without a standardized verification entrypoint and evidence requirements:
- Agent work cannot be reliably verified before merge
- There's no clear contract for what "done" means at the repo level
- Specs and evidence are not tracked systematically
- CI cannot enforce quality gates consistently

## Current state

- `yt-factory` has a robust ClickUp-based task execution protocol in `AGENTS.md`
- `Makefile` has a `make test` target but it requires API keys (runs `ytf doctor`)
- No standardized verify script that works offline
- No specs/evidence folder structure
- No CI workflow

## Desired state

- `scripts/verify.sh` runs offline (no API keys, no network)
- Specs folder with templates and example adoption spec
- Cursor rules enforce branch-only, testing, and DoD
- CI runs verify on every PR
- Evidence is required for all changes
