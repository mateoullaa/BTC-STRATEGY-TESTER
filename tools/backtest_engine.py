"""Simulates trades from a signal series against OHLCV price data.

Contract:
    run_backtest(df, initial_capital, commission_pct, slippage_pct,
                 position_size_pct, leverage) -> BacktestResult
        df must already have a `signal` column (1/-1/0, see strategy_loader.py).
        Supports long and short positions.

    BacktestResult holds at least: trades (list/DataFrame of executed trades)
    and equity_curve (pd.Series indexed by timestamp).

Position is `signal.shift(1)` to avoid lookahead: the position held during bar
t is decided from the signal known at t-1. Leverage is a linear P&L multiplier
only — no margin-call/liquidation is simulated (known, accepted limitation for
v1; surfaced to the user in the UI).

The equity curve and the trades table are computed independently: the equity
curve compounds transition costs bar-by-bar (needed for accurate drawdown/
Sharpe/Sortino/CAGR), while each trade charges a flat round-trip cost against
the equity at entry (needed for a trade-by-trade P&L that's simple and
hand-verifiable). `trades.pnl_abs.sum()` will therefore not exactly match the
equity curve's total return — an accepted tradeoff, not a bug.

Note this divergence is larger for short trades than long ones: the equity
curve rebalances exposure every bar (equivalent to a daily-rebalanced short),
so its compounded return over a segment can differ noticeably from the simple
entry-to-exit price ratio a static short would realize — a well-known
volatility-drag effect, not a calculation error.
"""

from dataclasses import dataclass

import pandas as pd

TRADE_COLUMNS = [
    "entry_time", "exit_time", "direction",
    "entry_price", "exit_price", "bars_held", "pnl_abs", "pnl_pct",
]


@dataclass
class BacktestResult:
    trades: pd.DataFrame
    equity_curve: pd.Series


def _build_trades(
    df: pd.DataFrame,
    position: pd.Series,
    equity_curve: pd.Series,
    leverage: float,
    position_size_pct: float,
    commission_pct: float,
    slippage_pct: float,
) -> pd.DataFrame:
    close = df["close"]
    segment_id = (position != position.shift()).cumsum()

    records = []
    for _, segment in position.groupby(segment_id):
        pos_value = segment.iloc[0]
        if pos_value == 0:
            continue

        entry_iloc = df.index.get_loc(segment.index[0])
        exit_iloc = df.index.get_loc(segment.index[-1])

        entry_price = close.iloc[entry_iloc - 1] if entry_iloc > 0 else close.iloc[0]
        exit_price = close.iloc[exit_iloc]
        entry_equity = equity_curve.iloc[entry_iloc - 1] if entry_iloc > 0 else equity_curve.iloc[0]

        direction = "long" if pos_value == 1 else "short"
        allocated = entry_equity * position_size_pct
        raw_pct_move = (exit_price / entry_price - 1) * (1 if direction == "long" else -1)
        leveraged_pct = raw_pct_move * leverage
        gross_pnl = allocated * leveraged_pct
        round_trip_cost = allocated * leverage * (commission_pct + slippage_pct) * 2
        pnl_abs = gross_pnl - round_trip_cost
        pnl_pct = pnl_abs / allocated if allocated else 0.0

        records.append({
            "entry_time": segment.index[0],
            "exit_time": segment.index[-1],
            "direction": direction,
            "entry_price": entry_price,
            "exit_price": exit_price,
            "bars_held": exit_iloc - entry_iloc + 1,
            "pnl_abs": pnl_abs,
            "pnl_pct": pnl_pct,
        })

    return pd.DataFrame(records, columns=TRADE_COLUMNS)


def run_backtest(
    df: pd.DataFrame,
    initial_capital: float,
    commission_pct: float,
    slippage_pct: float,
    position_size_pct: float,
    leverage: float,
) -> BacktestResult:
    position = df["signal"].shift(1).fillna(0)
    bar_return = df["close"].pct_change().fillna(0)

    transitions = position.diff()
    transitions.iloc[0] = position.iloc[0]
    transitions = transitions.abs()

    cost_bar = transitions * leverage * position_size_pct * (commission_pct + slippage_pct)
    gross_bar = position * leverage * position_size_pct * bar_return
    net_bar = gross_bar - cost_bar

    equity_curve = initial_capital * (1 + net_bar).cumprod()

    bankrupt_mask = equity_curve <= 0
    if bankrupt_mask.any():
        first_bankrupt_iloc = bankrupt_mask.values.argmax()
        equity_curve.iloc[first_bankrupt_iloc:] = 0.0

    trades = _build_trades(
        df, position, equity_curve, leverage, position_size_pct, commission_pct, slippage_pct
    )

    return BacktestResult(trades=trades, equity_curve=equity_curve)
