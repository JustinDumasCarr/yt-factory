# Future: server runs and remote storage

We are not using Docker in v1.
We design for it so it is easy later.

## Docker later
- Add a Dockerfile when the pipeline is stable.
- Make sure FFmpeg is installed in the container.
- Mount a projects volume for persistence.

## Remote storage later
Add StorageAdapter with two implementations:
- LocalStorage (v1)
- S3Storage (later)

Migration approach:
- keep project.json as canonical state
- move large assets (tracks, mp4) to S3
- store pointers in project.json:
  - s3://bucket/key
- keep local cache optional

## Running on a server
- run CLI commands via cron
- maintain a "queue" folder of new project configs
- process projects sequentially or with limited concurrency
