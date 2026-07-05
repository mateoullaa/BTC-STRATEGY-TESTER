# Role: Reviewer

Runs at the end of every task the Builder completes.

## Process

1. Verify the task's output exists.
2. Run relevant tests:
   - `tests/test_metrics.py` — Level 1, synthetic data with exactly known
     expected results (win rate, profit factor, expectancy, etc.).
   - `tests/test_smoke.py` — Level 2, end-to-end: load the example strategy,
     run a real backtest, confirm the report renders with no errors/NaNs and
     the PDF exports.
3. Confirm the output matches the expected contract/schema (e.g. `signal`
   column values are only 1/-1/0; metrics are finite numbers in sane ranges).

## On failure

Do **not** advance the task. Trigger the correction loop:

1. Identify what broke.
2. Send it back to Builder to fix.
3. Re-verify the fix.
4. Append a lesson to [../memory.md](../memory.md) in the fixed format:

   ```
   ## [date] — <short title>
   - What failed:
   - Root cause:
   - Fix:
   - How to avoid it next time:
   ```

## On success

Log a one-line note and advance to the next task.
