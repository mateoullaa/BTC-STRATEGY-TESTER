"""Computes report metrics from a BacktestResult (see backtest_engine.py).

Contract:
    compute_metrics(result: BacktestResult) -> dict
        Keys at least: expectancy, win_rate, profit_factor, total_return_pct,
        total_return_abs, max_drawdown_pct, max_drawdown_duration,
        sharpe_ratio, sortino_ratio, num_trades, avg_win, avg_loss, cagr.

Validated by tests/test_metrics.py against synthetic trades with hand-computed
expected values — this is the project's Level 1 success criterion.

Periodicity for annualizing Sharpe/Sortino/CAGR is inferred from the equity
curve's own DatetimeIndex (median bar spacing), so it's correct for any
timeframe without the contract needing an explicit timeframe argument.
Risk-free rate is assumed to be 0 (documented simplification).
"""

import pandas as pd

from tools.backtest_engine import BacktestResult

SECONDS_PER_YEAR = 365 * 24 * 3600


def _periods_per_year(equity_curve: pd.Series) -> float:
    median_seconds = equity_curve.index.to_series().diff().median().total_seconds()
    return SECONDS_PER_YEAR / median_seconds if median_seconds else 0.0


def _max_drawdown(equity_curve: pd.Series) -> tuple:
    running_max = equity_curve.cummax()
    drawdown = equity_curve / running_max - 1
    max_drawdown_pct = -drawdown.min() * 100

    at_peak = pd.Series(equity_curve.index, index=equity_curve.index).where(equity_curve >= running_max)
    peak_time = at_peak.ffill()
    duration_days = (equity_curve.index.to_series() - peak_time).dt.total_seconds() / 86400
    max_drawdown_duration = duration_days.max()

    return max_drawdown_pct, max_drawdown_duration


def compute_metrics(result: BacktestResult) -> dict:
    trades = result.trades
    equity_curve = result.equity_curve

    num_trades = len(trades)
    wins = trades.loc[trades["pnl_abs"] > 0, "pnl_abs"] if num_trades else pd.Series(dtype=float)
    losses = trades.loc[trades["pnl_abs"] < 0, "pnl_abs"] if num_trades else pd.Series(dtype=float)

    win_rate = len(wins) / num_trades if num_trades else 0.0
    avg_win = wins.mean() if len(wins) else 0.0
    avg_loss = losses.mean() if len(losses) else 0.0
    expectancy = trades["pnl_abs"].mean() if num_trades else 0.0

    gross_profit = wins.sum()
    gross_loss = abs(losses.sum())
    if gross_loss > 0:
        profit_factor = gross_profit / gross_loss
    else:
        profit_factor = float("inf") if gross_profit > 0 else 0.0

    total_return_abs = equity_curve.iloc[-1] - equity_curve.iloc[0]
    total_return_pct = equity_curve.iloc[-1] / equity_curve.iloc[0] - 1

    max_drawdown_pct, max_drawdown_duration = _max_drawdown(equity_curve)

    periods_per_year = _periods_per_year(equity_curve)
    bar_returns = equity_curve.pct_change().dropna()

    bar_std = bar_returns.std(ddof=1)
    sharpe_ratio = (
        bar_returns.mean() / bar_std * periods_per_year ** 0.5 if bar_std else 0.0
    )

    downside_dev = (bar_returns.clip(upper=0) ** 2).mean() ** 0.5
    sortino_ratio = (
        bar_returns.mean() / downside_dev * periods_per_year ** 0.5 if downside_dev else 0.0
    )

    n_years = (equity_curve.index[-1] - equity_curve.index[0]).total_seconds() / SECONDS_PER_YEAR
    if n_years > 0 and equity_curve.iloc[0] > 0 and equity_curve.iloc[-1] > 0:
        cagr = (equity_curve.iloc[-1] / equity_curve.iloc[0]) ** (1 / n_years) - 1
    elif equity_curve.iloc[-1] <= 0:
        cagr = -1.0
    else:
        cagr = 0.0

    return {
        "expectancy": expectancy,
        "win_rate": win_rate,
        "profit_factor": profit_factor,
        "total_return_pct": total_return_pct,
        "total_return_abs": total_return_abs,
        "max_drawdown_pct": max_drawdown_pct,
        "max_drawdown_duration": max_drawdown_duration,
        "sharpe_ratio": sharpe_ratio,
        "sortino_ratio": sortino_ratio,
        "num_trades": num_trades,
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "cagr": cagr,
    }
