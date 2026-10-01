# BTC/USDT Strategy Backtester

A Streamlit tool that loads a user-provided Python trading strategy, backtests it
against historical BTC/USDT data from Binance, and produces a full metrics report
(viewable in-app and exportable to PDF) to determine whether the strategy has
positive mathematical expectancy.

## Before any change

Run `python init.py` first. It checks the project structure, required docs, and
tests. **If it fails, stop and ask the user for help — do not continue.**

## Session start

Read [memory.md](memory.md) first and apply its lessons before doing anything else.

## Roles (sequential, not parallel)

One agent adopts these roles in order by reading the matching file. No parallel
subagents — see [roles/planner.md](roles/planner.md) for why.

1. [roles/planner.md](roles/planner.md) — turns an objective into an audited task list.
2. [roles/builder.md](roles/builder.md) — implements one task at a time.
3. [roles/reviewer.md](roles/reviewer.md) — verifies each task, updates memory.md on failure.

## The WAT separation

- **Workflows**: for this project, the Streamlit UI (`app.py`) itself is the
  orchestration flow — no separate `workflows/` folder.
- **Tools** (`tools/`): deterministic Python — data fetching, backtest engine,
  metrics, PDF report generation. All logic lives here, not in the agent's head.
- **Roles**: the agent (see above) connects intent to executing these tools.

## Project layout

- `tools/data_fetcher.py` — Binance public API OHLCV fetch + local cache.
- `tools/strategy_loader.py` — loads/validates a user strategy against the
  `generate_signals(df) -> df` contract (adds a `signal` column: 1/-1/0).
- `tools/backtest_engine.py` — simulates long/short trades from signals given
  capital, commission, slippage, position size, leverage.
- `tools/metrics.py` — expectancy, win rate, profit factor, drawdown, Sharpe,
  Sortino, CAGR, etc.
- `tools/report_generator.py` — builds the PDF report.
- `app.py` — Streamlit UI wiring the above together.
- `strategies/example_sma_crossover.py` — sample strategy used by the smoke test.
- `tests/test_metrics.py` — Level 1: synthetic data, exact expected results.
- `tests/test_smoke.py` — Level 2: end-to-end run, no errors/NaNs, PDF exports.

## Language rule

All artifacts (code, docs, commits, comments) are in **English**. Conversation
with the user is in **English** too (Mateo's global rule since 2026-10-01).

## Skills / MCP

Check whether an existing skill or MCP already solves a task before writing new
code. Use one only if it genuinely helps — never preload dependencies "just in case".

## Self-improvement loop

Every failure caught by the Reviewer gets logged in [memory.md](memory.md) in a
fixed format after the fix is verified. See that file for the format and current
lessons.
