# BTC/USDT Strategy Backtester

A Streamlit tool to backtest custom BTC/USDT trading strategies against
historical Binance data and get a full report — expectancy, win rate, profit
factor, drawdown, Sharpe/Sortino, CAGR, and an equity curve chart — viewable
in-app and exportable to PDF.

## Status

Functional v1. All `tools/` implementations and the Streamlit UI are built and
verified end-to-end (both test levels pass, `python init.py` is green). Known
limitation: leverage is modeled as a linear P&L multiplier with no margin-call/
liquidation simulation. See [memory.md](memory.md) for the running log of
lessons from the build.

## How it works

1. Upload a `.py` file or paste Python code defining your strategy:

   ```python
   def generate_signals(df):
       # df: columns = open, high, low, close, volume
       sma_fast = df["close"].rolling(10).mean()
       sma_slow = df["close"].rolling(50).mean()
       df["signal"] = 0
       df.loc[sma_fast > sma_slow, "signal"] = 1
       df.loc[sma_fast < sma_slow, "signal"] = -1
       return df
   ```

   `signal` values: `1` = long, `-1` = short, `0` = flat.

2. Configure the backtest: initial capital, commission, slippage, position
   size, leverage, date range, and timeframe.

3. Run it against historical BTC/USDT data pulled from Binance's public API,
   and review the report in the app or export it as a PDF.

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate      # Windows
pip install -r requirements.txt
streamlit run app.py
```

## Project structure

- `tools/data_fetcher.py` — Binance OHLCV fetch + local cache.
- `tools/strategy_loader.py` — loads/validates a strategy against the
  `generate_signals(df) -> df` contract.
- `tools/backtest_engine.py` — simulates long/short trades from signals.
- `tools/metrics.py` — computes all report metrics.
- `tools/report_generator.py` — builds the PDF report.
- `app.py` — Streamlit UI wiring the pieces above together.
- `strategies/example_sma_crossover.py` — sample strategy (SMA crossover).

## Testing

Two levels, both required:

- `tests/test_metrics.py` — synthetic trades with exactly known expected
  metrics (win rate, profit factor, expectancy, drawdown), so the calculation
  engine is verified, not just "doesn't crash".
- `tests/test_smoke.py` — end-to-end run on the example strategy against a
  bundled historical data fixture (`tests/fixtures/btcusdt_1h_sample.csv`, kept
  offline/deterministic instead of hitting Binance live): confirms the full
  pipeline produces a report with no errors/NaNs and exports a PDF.

Run `python init.py` before making any change — it checks the project
structure and runs this test suite.

## Contributing / development model

Development follows a sequential Planner → Builder → Reviewer loop (see
[roles/](roles/)) instead of parallel agents, with lessons from each fixed
failure logged to [memory.md](memory.md). See [CLAUDE.md](CLAUDE.md) for the
full harness description.
