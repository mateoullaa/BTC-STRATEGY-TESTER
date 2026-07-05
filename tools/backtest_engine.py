"""Simulates trades from a signal series against OHLCV price data.

Contract:
    run_backtest(df, initial_capital, commission_pct, slippage_pct,
                 position_size_pct, leverage) -> BacktestResult
        df must already have a `signal` column (1/-1/0, see strategy_loader.py).
        Supports long and short positions.

    BacktestResult holds at least: trades (list/DataFrame of executed trades)
    and equity_curve (pd.Series indexed by timestamp).

Status: not yet implemented. Built by the Builder role per roles/builder.md.
"""

from dataclasses import dataclass

import pandas as pd


@dataclass
class BacktestResult:
    trades: pd.DataFrame
    equity_curve: pd.Series


def run_backtest(
    df: pd.DataFrame,
    initial_capital: float,
    commission_pct: float,
    slippage_pct: float,
    position_size_pct: float,
    leverage: float,
) -> BacktestResult:
    raise NotImplementedError
