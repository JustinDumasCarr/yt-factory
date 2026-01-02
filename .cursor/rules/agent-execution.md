# Agent Execution Rules. You must follow these steps.

## Task selection
- Only work on tasks in ClickUp list 901519223413 with status READY.
- If no READY tasks exist, stop and report: "No READY tasks."

## Definition of Ready
A task is READY only if it includes:
- Goal
- Scope (IN and OUT)
- Acceptance Criteria
- Verify commands

If any of these are missing:
- Comment on the ClickUp task with exactly what is missing.
- Move it to SPEC NEEDED.
- Stop.

## Execution protocol (for a READY task)
1) Restate the Goal and Acceptance Criteria in your own words.
2) Propose a minimal implementation plan (max 8 bullets).
3) Identify files to change before editing.
4) Implement in small commits.
5) Run Verify commands exactly as written in the task.
6) Post a ClickUp comment with:
   - What changed
   - Files changed
   - Commands run + results
   - Any follow-ups
7) Move status:
   - NEEDS REVIEW if a PR/branch is ready for review
   - BLOCKED if Verify fails 3 times
