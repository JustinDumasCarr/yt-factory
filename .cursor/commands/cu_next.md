You have access to ClickUp via MCP.

Goal: pick the next READY task from ClickUp list 901519223413 and start execution.

Steps:
1) Query ClickUp for tasks in list 901519223413 with status READY.
2) If multiple tasks exist, select the highest priority. If no priority, pick the oldest created.
3) Print:
   - Task name
   - Task ID
   - Goal
   - Acceptance Criteria
   - Verify commands
4) Immediately change the task status to "in progress".
5) Create a local file TASK.md with the extracted spec and begin work following the repo rules.
If there are zero READY tasks, output: "No READY tasks. Move tasks from SPEC NEEDED to READY after adding Goal, Scope, Acceptance Criteria, Verify."
