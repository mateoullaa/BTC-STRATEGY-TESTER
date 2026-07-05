# Role: Planner

Turn the current objective into a concrete, ordered task list, then hand off to
[builder.md](builder.md).

## Why sequential, not parallel subagents

One agent adopts Planner → Builder → Reviewer in sequence, reading each role file
in turn. This project doesn't have genuinely independent, parallelizable work, so
parallel subagents would just burn tokens for no real speedup. (Exception: if a
future task is genuinely parallelizable, real subagents may be worth it — that's
not the default here.)

## Process

1. Read [../CLAUDE.md](../CLAUDE.md) and [../memory.md](../memory.md) for context
   and past lessons.
2. Break the objective into small tasks, each with a concrete success criterion
   (what file/behavior proves it's done).
3. Order tasks by real dependency (e.g. `tools/data_fetcher.py` before
   `tools/backtest_engine.py`, since the engine consumes its output).

## Self-audit (mandatory, before handing off to Builder)

Check the task list against:

- **Scope** — is every task implied by the approved intake/structure in
  CLAUDE.md? Flag or cut anything that isn't; ask the user before keeping it.
- **Coverage** — does every requirement from the original intake map to at least
  one task?
- **Sequencing** — does the task order respect real dependencies?

Log a one-line pass/fail note for the audit. If something was cut for scope,
name what was cut — a bare "pass" is not enough.

Do not proceed to Builder until the audit passes.
