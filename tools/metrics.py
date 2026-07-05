"""Computes report metrics from a BacktestResult (see backtest_engine.py).

Contract:
    compute_metrics(result: BacktestResult) -> dict
        Keys at least: expectancy, win_rate, profit_factor, total_return_pct,
        total_return_abs, max_drawdown_pct, max_drawdown_duration,
        sharpe_ratio, sortino_ratio, num_trades, avg_win, avg_loss, cagr.

Validated by tests/test_metrics.py against synthetic trades with hand-computed
expected values — this is the project's Level 1 success criterion.

Status: not yet implemented. Built by the Builder role per roles/builder.md.
"""

from tools.backtest_engine import BacktestResult


def compute_metrics(result: BacktestResult) -> dict:
    raise NotImplementedError
