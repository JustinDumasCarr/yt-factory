# Overview

This project is a local-first content factory.

Core idea:
- Each compilation is a "project folder" with a `project.json` file as the single source of truth.
- Each step writes outputs and logs inside that project folder.
- Steps are resumable. You can rerun a failed step without starting over.

Default behavior:
- Target compilation length: 60 minutes.
- Vocals: optional per project.
- Track selection: include all by default. Optional `approved.txt` gate is supported.
- Output: 1080p, 30fps MP4.
- Upload: default to Unlisted.

Key constraints:
- Keep code boring and debuggable.
- Avoid complex infrastructure in v1.
- Design interfaces so we can add Docker, S3 storage, and a GUI later.
