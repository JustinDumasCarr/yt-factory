"""
Task runner for docs/TASKS.md.

Supports a minimal agent workflow:
- next: print the first unchecked task id (T###)
- verify T###: run all "Verify:" commands for that task
- done T###: flip - [ ] -> - [x] for that task (requires --force by default)

Design goals:
- Conservative parsing (line-oriented, no Markdown AST)
- No hidden state / caches
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

TASK_HEADER_RE = re.compile(r"^- \[(?P<mark>[ xX~!])\] (?P<task_id>T\d{3})\b(?P<title>.*)$")
VERIFY_LINE_RE = re.compile(r"^\s+- Verify:\s*(?P<cmd>.+?)\s*$")


@dataclass(frozen=True)
class TaskBlock:
    task_id: str
    mark: str
    header_line_index: int
    end_line_index_exclusive: int
    verify_commands: tuple[str, ...]


def _read_lines(path: Path) -> list[str]:
    try:
        return path.read_text(encoding="utf-8").splitlines(keepends=True)
    except FileNotFoundError:
        raise RuntimeError(f"Tasks file not found: {path}")


def _iter_task_headers(lines: list[str]) -> Iterable[tuple[int, re.Match[str]]]:
    for i, line in enumerate(lines):
        m = TASK_HEADER_RE.match(line.rstrip("\n"))
        if m:
            yield i, m


def _parse_tasks(lines: list[str]) -> dict[str, TaskBlock]:
    headers = list(_iter_task_headers(lines))
    tasks: dict[str, TaskBlock] = {}

    for idx, (line_i, m) in enumerate(headers):
        next_header_i = headers[idx + 1][0] if idx + 1 < len(headers) else len(lines)
        task_id = m.group("task_id")
        mark = m.group("mark")

        verify_cmds: list[str] = []
        for block_line in lines[line_i + 1 : next_header_i]:
            vm = VERIFY_LINE_RE.match(block_line.rstrip("\n"))
            if vm:
                verify_cmds.append(vm.group("cmd").strip())

        tasks[task_id] = TaskBlock(
            task_id=task_id,
            mark=mark,
            header_line_index=line_i,
            end_line_index_exclusive=next_header_i,
            verify_commands=tuple(verify_cmds),
        )

    return tasks


def cmd_next(tasks_file: Path) -> int:
    lines = _read_lines(tasks_file)
    tasks = _parse_tasks(lines)

    for task_id in sorted(tasks.keys()):
        # IDs are sortable lexicographically for T### (T001 < T010 < T100)
        if tasks[task_id].mark == " ":
            print(task_id)
            return 0

    print("No unchecked tasks found (no '- [ ] T### ...' entries).", file=sys.stderr)
    return 1


def cmd_verify(tasks_file: Path, task_id: str) -> int:
    lines = _read_lines(tasks_file)
    tasks = _parse_tasks(lines)

    if task_id not in tasks:
        print(f"Task not found: {task_id}", file=sys.stderr)
        return 2

    block = tasks[task_id]
    if not block.verify_commands:
        print(
            f"No Verify commands found for {task_id}. Add lines like: '  - Verify: <command>'",
            file=sys.stderr,
        )
        return 2

    for cmd in block.verify_commands:
        print(f"[verify] {cmd}", file=sys.stderr)
        proc = subprocess.run(cmd, shell=True)
        if proc.returncode != 0:
            print(f"[verify] FAILED ({task_id}): {cmd}", file=sys.stderr)
            return proc.returncode

    print(f"[verify] OK ({task_id})", file=sys.stderr)
    return 0


def cmd_done(tasks_file: Path, task_id: str, force: bool) -> int:
    lines = _read_lines(tasks_file)

    for i, line in enumerate(lines):
        m = TASK_HEADER_RE.match(line.rstrip("\n"))
        if not m:
            continue
        if m.group("task_id") != task_id:
            continue

        mark = m.group("mark")
        if mark.lower() == "x":
            print(f"Task already marked done: {task_id}", file=sys.stderr)
            return 0

        if not force:
            print(
                f"Refusing to mark done without --force (no verification cache). "
                f"Run 'make verify TASK={task_id}' then re-run with FORCE=1.",
                file=sys.stderr,
            )
            return 2

        # Replace only the checkbox portion on this line.
        # Example: "- [ ] T001 ..." -> "- [x] T001 ..."
        lines[i] = re.sub(r"^- \[ \] ", "- [x] ", lines[i])
        tasks_file.write_text("".join(lines), encoding="utf-8")
        print(f"Marked done: {task_id}", file=sys.stderr)
        return 0

    print(f"Task not found: {task_id}", file=sys.stderr)
    return 2


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)

    # Accept --file in either position:
    # - python -m ytf.tools.tasks --file docs/TASKS.md next
    # - python -m ytf.tools.tasks next --file docs/TASKS.md
    tasks_file_arg = "docs/TASKS.md"
    cleaned: list[str] = []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--file":
            if i + 1 >= len(argv):
                print("error: --file requires a value", file=sys.stderr)
                return 2
            tasks_file_arg = argv[i + 1]
            i += 2
            continue
        if a.startswith("--file="):
            tasks_file_arg = a.split("=", 1)[1]
            i += 1
            continue
        cleaned.append(a)
        i += 1

    parser = argparse.ArgumentParser(prog="python -m ytf.tools.tasks")

    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("next", help="Print the first unchecked task id (T###)")

    p_verify = sub.add_parser("verify", help="Run Verify commands for a task")
    p_verify.add_argument("task_id", help="Task id like T001")

    p_done = sub.add_parser("done", help="Mark a task as done (requires --force by default)")
    p_done.add_argument("task_id", help="Task id like T001")
    p_done.add_argument(
        "--force", action="store_true", help="Allow editing TASKS.md to mark task done"
    )

    args = parser.parse_args(cleaned)
    tasks_file = Path(tasks_file_arg)

    if args.cmd == "next":
        return cmd_next(tasks_file)
    if args.cmd == "verify":
        return cmd_verify(tasks_file, args.task_id)
    if args.cmd == "done":
        return cmd_done(tasks_file, args.task_id, force=bool(args.force))

    print(f"Unknown command: {args.cmd}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
