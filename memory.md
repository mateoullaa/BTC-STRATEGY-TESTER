# Memory

Self-improvement log for this project. Entries are appended by the Reviewer role
after a failure is found, fixed, and re-verified — never written by hand ahead of
time. Read this file at the start of every session and apply its lessons.

Entry format:

```
## [date] — <short title>
- What failed:
- Root cause:
- Fix:
- How to avoid it next time:
```

---

## 2026-07-05 — Drawdown duration crashed with AttributeError

- What failed: `tools/metrics.py::_max_drawdown` raised
  `AttributeError: 'Series' object has no attribute 'total_seconds'`.
- Root cause: `(equity_curve.index - peak_time)` produces a pandas `Series` of
  `Timedelta` values, not a `TimedeltaIndex`. `.total_seconds()` is only
  available on a `TimedeltaIndex`/scalar `Timedelta`, not directly on a
  `Series` — it needs the `.dt` accessor.
- Fix: changed to `(equity_curve.index.to_series() - peak_time).dt.total_seconds()`.
- How to avoid it next time: when subtracting two datetime-like `Series`
  (as opposed to an `Index`), always route through `.dt.<accessor>` for
  timedelta properties.

## 2026-07-05 — CAGR test failed due to leap year

- What failed: `test_cagr_exact_one_year_span` expected `cagr == 0.2` for a
  2024-01-01 → 2025-01-01 span, got `0.19940...`.
- Root cause: 2024 is a leap year (366 days), so the span was `366/365 ≈
  1.0027` years, not exactly 1 — the CAGR formula (correctly) compounded over
  slightly more than a year.
- Fix: changed the test to use 2025-01-01 → 2026-01-01 (not a leap year, exact
  365-day span).
- How to avoid it next time: when hand-deriving an expected value for a
  date-span-based metric, pick a span that avoids leap-year ambiguity, or
  compute the expected value using the exact day count instead of assuming
  a round number of years.

## 2026-07-05 — data_fetcher crashed converting an already-aware Timestamp

- What failed: `fetch_ohlcv` raised `ValueError: Cannot pass a datetime or
  Timestamp with tzinfo with the tz parameter` on its first real network call.
- Root cause: `_to_ms` always called `pd.Timestamp(ts, tz="UTC")`, but callers
  sometimes pass an already tz-aware `Timestamp` (e.g. `cached_min`/`cached_max`
  read back from the parquet cache's UTC index) — pandas rejects re-localizing
  an aware timestamp via the `tz=` constructor argument.
- Fix: `_to_ms` now branches: `tz_localize("UTC")` if naive, `tz_convert("UTC")`
  if already aware.
- How to avoid it next time: a timestamp-normalizing helper that's called with
  both raw strings and already-localized `Timestamp` objects must handle both
  cases explicitly — don't assume the input is always naive.
