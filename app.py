"""Streamlit UI: load a strategy, configure the backtest, run it, view/export the report.

Wires together tools/data_fetcher.py, tools/strategy_loader.py,
tools/backtest_engine.py, tools/metrics.py and tools/report_generator.py.
No backtesting logic lives here — this file only orchestrates the tools/ layer.

Status: not yet implemented. Built by the Builder role per roles/builder.md.
"""

import streamlit as st


def main() -> None:
    st.title("BTC/USDT Strategy Backtester")
    st.write("Not yet implemented.")


if __name__ == "__main__":
    main()
