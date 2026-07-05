"""Level 2 success criterion: end-to-end run with no errors/NaNs, PDF exports.

Uses a bundled local fixture (tests/fixtures/btcusdt_1h_sample.csv) instead of
a live Binance call, so this test is fast, deterministic, and doesn't depend
on network access or Binance's API being reachable from CI.
"""

from pathlib import Path

import pandas as pd

from strategies.example_sma_crossover import generate_signals
from tools.backtest_engine import run_backtest
from tools.metrics import compute_metrics
from tools.report_generator import generate_pdf_report
from tools.strategy_loader import validate_signals

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "btcusdt_1h_sample.csv"


def _load_fixture() -> pd.DataFrame:
    return pd.read_csv(FIXTURE_PATH, index_col="open_time", parse_dates=["open_time"])


def test_end_to_end_pipeline_no_errors_or_nans(tmp_path):
    ohlcv = _load_fixture()

    signals_df = generate_signals(ohlcv)
    validate_signals(signals_df)

    result = run_backtest(
        signals_df,
        initial_capital=10_000,
        commission_pct=0.001,
        slippage_pct=0.0005,
        position_size_pct=1.0,
        leverage=1.0,
    )

    metrics = compute_metrics(result)

    for key, value in metrics.items():
        assert value == value, f"metric '{key}' is NaN"  # NaN != NaN

    assert 0 <= metrics["max_drawdown_pct"] <= 100
    assert metrics["num_trades"] > 0

    output_path = tmp_path / "report.pdf"
    generate_pdf_report(metrics, result.equity_curve, str(output_path))

    assert output_path.exists()
    assert output_path.stat().st_size > 0
