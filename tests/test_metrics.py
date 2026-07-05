"""Level 1 success criterion: hand-computed synthetic cases for compute_metrics,
plus one exact-value case that exercises run_backtest itself (closing the gap
that metrics-only tests don't touch backtest_engine's own math).
"""

import pandas as pd
import pytest

from tools.backtest_engine import BacktestResult, run_backtest
from tools.metrics import compute_metrics


def _flat_equity_curve(value=10_000, bars=2):
    index = pd.date_range("2024-01-01", periods=bars, freq="D", tz="UTC")
    return pd.Series([value] * bars, index=index)


def test_trade_metrics_exact_win_rate_profit_factor_expectancy():
    trades = pd.DataFrame({"pnl_abs": [100.0, 80.0, 60.0, -50.0, -30.0]})
    result = BacktestResult(trades=trades, equity_curve=_flat_equity_curve())

    metrics = compute_metrics(result)

    assert metrics["num_trades"] == 5
    assert metrics["win_rate"] == pytest.approx(0.6)
    assert metrics["profit_factor"] == pytest.approx(240 / 80)
    assert metrics["expectancy"] == pytest.approx(32.0)
    assert metrics["avg_win"] == pytest.approx(80.0)
    assert metrics["avg_loss"] == pytest.approx(-40.0)


def test_profit_factor_and_win_rate_edge_cases():
    no_losses = BacktestResult(
        trades=pd.DataFrame({"pnl_abs": [50.0, 20.0]}),
        equity_curve=_flat_equity_curve(),
    )
    assert compute_metrics(no_losses)["profit_factor"] == float("inf")

    no_trades = BacktestResult(
        trades=pd.DataFrame({"pnl_abs": []}),
        equity_curve=_flat_equity_curve(),
    )
    metrics = compute_metrics(no_trades)
    assert metrics["num_trades"] == 0
    assert metrics["win_rate"] == 0.0
    assert metrics["profit_factor"] == 0.0
    assert metrics["expectancy"] == 0.0


def test_drawdown_pct_and_duration_exact():
    index = pd.date_range("2024-01-01", periods=6, freq="D", tz="UTC")
    equity_curve = pd.Series([10_000, 12_000, 9_000, 7_000, 11_000, 15_000], index=index)
    result = BacktestResult(trades=pd.DataFrame({"pnl_abs": []}), equity_curve=equity_curve)

    metrics = compute_metrics(result)

    assert metrics["max_drawdown_pct"] == pytest.approx(41.666667, rel=1e-6)
    assert metrics["max_drawdown_duration"] == pytest.approx(3.0)


def test_cagr_exact_one_year_span():
    # 2025 is not a leap year, so this span is exactly 365 days == 1.0 year.
    index = pd.DatetimeIndex(
        [pd.Timestamp("2025-01-01", tz="UTC"), pd.Timestamp("2026-01-01", tz="UTC")]
    )
    equity_curve = pd.Series([10_000, 12_000], index=index)
    result = BacktestResult(trades=pd.DataFrame({"pnl_abs": []}), equity_curve=equity_curve)

    metrics = compute_metrics(result)

    assert metrics["cagr"] == pytest.approx(0.2, rel=1e-3)
    assert metrics["total_return_pct"] == pytest.approx(0.2)
    assert metrics["total_return_abs"] == pytest.approx(2_000)


def test_sharpe_and_sortino_exact_alternating_returns():
    index = pd.date_range("2024-01-01", periods=5, freq="D", tz="UTC")
    equity_curve = 10_000 * pd.Series([1.0, 1.10, 1.10 * 0.95, 1.10 * 0.95 * 1.10, 1.10 * 0.95 * 1.10 * 0.95], index=index)
    result = BacktestResult(trades=pd.DataFrame({"pnl_abs": []}), equity_curve=equity_curve)

    metrics = compute_metrics(result)

    # Hand-derived: returns = [0.10, -0.05, 0.10, -0.05], mean=0.025,
    # sample std (ddof=1) = sqrt(0.0075), periods_per_year = 365 (daily bars).
    assert metrics["sharpe_ratio"] == pytest.approx(5.5151, rel=1e-3)
    # downside deviation over all bars (MAR=0) = sqrt(0.00125)
    assert metrics["sortino_ratio"] == pytest.approx(13.5093, rel=1e-3)


def test_run_backtest_long_matches_hand_computed_equity_and_trade():
    index = pd.date_range("2024-01-01", periods=3, freq="D", tz="UTC")
    df = pd.DataFrame(
        {"close": [100.0, 110.0, 121.0], "signal": [1, 1, 0]},
        index=index,
    )

    result = run_backtest(
        df,
        initial_capital=10_000,
        commission_pct=0.0,
        slippage_pct=0.0,
        position_size_pct=1.0,
        leverage=1.0,
    )

    assert result.equity_curve.iloc[-1] == pytest.approx(12_100.0)
    assert len(result.trades) == 1
    trade = result.trades.iloc[0]
    assert trade["direction"] == "long"
    assert trade["entry_price"] == pytest.approx(100.0)
    assert trade["exit_price"] == pytest.approx(121.0)
    assert trade["pnl_abs"] == pytest.approx(2_100.0)


def test_run_backtest_short_trade_pnl_diverges_from_equity_curve_by_design():
    index = pd.date_range("2024-01-01", periods=3, freq="D", tz="UTC")
    df = pd.DataFrame(
        {"close": [100.0, 90.0, 81.0], "signal": [-1, -1, 0]},
        index=index,
    )

    result = run_backtest(
        df,
        initial_capital=10_000,
        commission_pct=0.0,
        slippage_pct=0.0,
        position_size_pct=1.0,
        leverage=1.0,
    )

    # Equity curve compounds two +10% bars (short benefits from the drop): 1.1 * 1.1 = 1.21
    assert result.equity_curve.iloc[-1] == pytest.approx(12_100.0)
    # Trade P&L uses the static entry/exit price ratio instead: (100-81)/100 = 19%
    trade = result.trades.iloc[0]
    assert trade["direction"] == "short"
    assert trade["pnl_abs"] == pytest.approx(1_900.0)
