# Sync Tasks

Synchronize task status between Vibe-Kanban (source of truth for STATUS) and TASKS.md (source of truth for DETAILS).

## When to Use
- Before making git commits that include task progress
- At the start of a session to verify current state
- When asked to sync or update task status

## Instructions

### Step 1: Get Current Vibe-Kanban Status

Use the MCP tools to fetch current task status:

```
1. Call list_projects to get the yt-factory project ID
2. Call list_tasks with the project_id to get all tasks and their statuses
```

### Step 2: Read TASKS.md

Read the current TASKS.md file to understand the documented tasks and their status markers.

### Step 3: Match and Update

For each task in TASKS.md, find the corresponding vibe-kanban task and update the status:

**Status Mapping:**
| Vibe-Kanban | TASKS.md |
|-------------|----------|
| `todo` | Status: Pending |
| `inprogress` | Status: In Progress |
| `inreview` | Status: In Review |
| `done` | Status: Complete |
| `cancelled` | Status: Cancelled |

### Step 4: Update TASKS.md

Edit TASKS.md to reflect the current status from vibe-kanban:

1. Update individual task status markers
2. Update the "Last Updated" date at the top
3. Move completed tasks to Archive section

### Step 5: Report Discrepancies

After syncing, report:
- Tasks in vibe-kanban but not in TASKS.md (may need to add)
- Tasks in TASKS.md but not in vibe-kanban (may need to create)
- Any status conflicts or ambiguities

### Step 6: Offer to Commit

Ask the user if they want to commit the sync:
```
git add TASKS.md && git commit -m "Sync task status from vibe-kanban"
```

## Output Format

After syncing, provide a summary:

```
## Task Sync Complete

**Updated:** X tasks
**Added to vibe-kanban:** Y tasks
**Discrepancies:** Z items

### Status Summary
| Task | Previous | Current |
|------|----------|---------|
| ... | ... | ... |

### Actions Needed
- [ ] Item 1
- [ ] Item 2
```

## Notes

- Vibe-Kanban is the source of truth for STATUS
- TASKS.md is the source of truth for DETAILS (acceptance criteria, test instructions)
- If a task exists in TASKS.md but not vibe-kanban, offer to create it
- If a task exists in vibe-kanban but not TASKS.md, note it but don't auto-add
