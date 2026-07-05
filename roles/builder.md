# Role: Builder

Implement one task at a time from the Planner's audited list.

## Process

1. Take the next pending task.
2. Check whether an existing tool in `tools/` already covers part of the work
   before writing anything new.
3. Implement the task, keeping each `tools/*.py` file focused on its one stated
   responsibility (see the project layout in [../CLAUDE.md](../CLAUDE.md)).
4. Do not mark a task done yourself — hand off to
   [reviewer.md](reviewer.md) to verify it.

## Rules

- Follow the contracts already fixed during intake (e.g.
  `generate_signals(df) -> df` with a `signal` column of 1/-1/0) — don't
  redesign them mid-build.
- Secrets (if any are ever needed) live only in `.env`, never hardcoded.
- No placeholder/half-finished logic left behind once a task is marked
  complete — either it's done and verified, or it's still in progress.
