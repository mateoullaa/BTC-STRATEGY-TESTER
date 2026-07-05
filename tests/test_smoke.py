"""Level 2 success criterion: end-to-end run with no errors/NaNs, PDF exports.

TODO (Builder role): once the tools/ pipeline is implemented, replace
test_placeholder with a real run:
    1. Fetch (or load a fixture of) BTC/USDT OHLCV data.
    2. Run strategies/example_sma_crossover.generate_signals on it.
    3. Run tools.backtest_engine.run_backtest on the signals.
    4. Run tools.metrics.compute_metrics on the result -> assert no NaNs and
       max_drawdown_pct is within [0, 100].
    5. Run tools.report_generator.generate_pdf_report -> assert the PDF file
       exists on disk.
"""


def test_placeholder():
    assert True
