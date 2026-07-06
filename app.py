"""Streamlit UI: load a strategy, configure the backtest, run it, view/export the report.

Wires together tools/data_fetcher.py, tools/strategy_loader.py,
tools/backtest_engine.py, tools/metrics.py and tools/report_generator.py.
No backtesting logic lives here — this file only orchestrates the tools/ layer.
"""

import tempfile
from datetime import date, timedelta
from pathlib import Path

import plotly.graph_objects as go
import streamlit as st

from tools.backtest_engine import run_backtest
from tools.data_fetcher import fetch_ohlcv
from tools.metrics import compute_metrics
from tools.report_generator import (
    METRIC_DESCRIPTIONS,
    METRIC_LABELS,
    format_metric_value,
    generate_pdf_report,
)
from tools.strategy_loader import load_strategy, validate_signals

SYMBOL = "BTCUSDT"
TIMEFRAMES = ["1m", "5m", "15m", "1h", "4h", "1d"]


def _load_strategy_code() -> str | None:
    source_mode = st.sidebar.radio("Strategy source", ["Upload .py file", "Paste code"])
    if source_mode == "Upload .py file":
        uploaded = st.sidebar.file_uploader("Strategy file", type=["py"])
        code = uploaded.getvalue().decode("utf-8") if uploaded is not None else None
    else:
        pasted = st.sidebar.text_area(
            "Strategy code", height=300, key="strategy_paste_area",
            help="After pasting, click outside this box (or press Ctrl+Enter) before clicking Run backtest.",
        )
        code = pasted.strip() or None

    if code:
        st.sidebar.caption(f"Strategy loaded: {len(code.splitlines())} lines.")
    return code


def _sidebar_config() -> dict:
    st.sidebar.header("Backtest configuration")
    initial_capital = st.sidebar.number_input("Initial capital ($)", min_value=1.0, value=10_000.0)
    commission_pct = st.sidebar.number_input("Commission (%)", min_value=0.0, value=0.1, step=0.01) / 100
    slippage_pct = st.sidebar.number_input("Slippage (%)", min_value=0.0, value=0.05, step=0.01) / 100
    position_size_pct = st.sidebar.slider("Position size (% of equity)", 1, 100, 100) / 100
    leverage = st.sidebar.number_input("Leverage", min_value=1.0, value=1.0, step=0.5)
    st.sidebar.caption(
        "Leverage is modeled as a linear P&L multiplier — no margin-call/liquidation "
        "is simulated. Results may be optimistic at high leverage against the position."
    )
    date_range = st.sidebar.date_input(
        "Date range", value=(date.today() - timedelta(days=30), date.today())
    )
    timeframe = st.sidebar.selectbox("Timeframe", TIMEFRAMES, index=TIMEFRAMES.index("1h"))
    st.sidebar.caption(
        "Wide date ranges on small timeframes (1m/5m) mean many pages of history to "
        "download from Binance the first time — this can take a couple of minutes with "
        "no visible progress beyond the small 'RUNNING' indicator. Subsequent runs over "
        "the same range are cached and much faster."
    )
    return {
        "initial_capital": initial_capital,
        "commission_pct": commission_pct,
        "slippage_pct": slippage_pct,
        "position_size_pct": position_size_pct,
        "leverage": leverage,
        "date_range": date_range,
        "timeframe": timeframe,
    }


def _run_backtest(code: str, config: dict) -> None:
    module = load_strategy(code, from_path=False)
    start, end = config["date_range"]

    ohlcv = fetch_ohlcv(SYMBOL, config["timeframe"], str(start), str(end))
    signals_df = module.generate_signals(ohlcv)
    validate_signals(signals_df)

    result = run_backtest(
        signals_df,
        initial_capital=config["initial_capital"],
        commission_pct=config["commission_pct"],
        slippage_pct=config["slippage_pct"],
        position_size_pct=config["position_size_pct"],
        leverage=config["leverage"],
    )
    metrics = compute_metrics(result)

    st.session_state["ohlcv"] = ohlcv
    st.session_state["result"] = result
    st.session_state["metrics"] = metrics


def _metric_card(container, key: str, value) -> None:
    container.metric(
        METRIC_LABELS.get(key, key.replace("_", " ").title()),
        format_metric_value(key, value),
        help=METRIC_DESCRIPTIONS.get(key),
    )


def _render_report(config: dict) -> None:
    metrics = st.session_state["metrics"]
    result = st.session_state["result"]
    ohlcv = st.session_state["ohlcv"]

    st.subheader("Key metrics")
    headline_keys = [
        "total_return_pct", "sharpe_ratio", "max_drawdown_pct",
        "win_rate", "profit_factor", "cagr",
    ]
    cols = st.columns(3)
    for i, key in enumerate(headline_keys):
        _metric_card(cols[i % 3], key, metrics[key])

    st.subheader("All metrics")
    all_keys = list(metrics.keys())
    cols = st.columns(4)
    for i, key in enumerate(all_keys):
        _metric_card(cols[i % 4], key, metrics[key])

    st.subheader("Equity curve vs. BTC/USDT price")
    price_norm = ohlcv["close"] / ohlcv["close"].iloc[0] * config["initial_capital"]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=result.equity_curve.index, y=result.equity_curve.values, name="Equity"))
    fig.add_trace(go.Scatter(x=price_norm.index, y=price_norm.values, name="BTC/USDT (normalized)"))
    st.plotly_chart(fig, width="stretch")

    st.subheader("Trades")
    trades_display = result.trades.copy()
    if "pnl_pct" in trades_display:
        trades_display["pnl_pct"] = trades_display["pnl_pct"] * 100
    st.dataframe(
        trades_display,
        width="stretch",
        column_config={
            "entry_time": st.column_config.DatetimeColumn("Entry Time"),
            "exit_time": st.column_config.DatetimeColumn("Exit Time"),
            "direction": st.column_config.TextColumn("Direction"),
            "entry_price": st.column_config.NumberColumn("Entry Price", format="$%.2f"),
            "exit_price": st.column_config.NumberColumn("Exit Price", format="$%.2f"),
            "bars_held": st.column_config.NumberColumn("Bars Held"),
            "pnl_abs": st.column_config.NumberColumn("P&L ($)", format="$%.2f"),
            "pnl_pct": st.column_config.NumberColumn("P&L (%)", format="%.2f%%"),
        },
    )

    if st.button("Export report to PDF"):
        pdf_path = Path(tempfile.gettempdir()) / "backtest_report.pdf"
        generate_pdf_report(metrics, result.equity_curve, str(pdf_path))
        st.download_button(
            "Download PDF",
            data=pdf_path.read_bytes(),
            file_name="backtest_report.pdf",
            mime="application/pdf",
        )


def main() -> None:
    st.title("BTC/USDT Strategy Backtester")

    code = _load_strategy_code()
    config = _sidebar_config()

    if st.sidebar.button("Run backtest"):
        if not code:
            st.error("Upload or paste a strategy first.")
        else:
            try:
                with st.spinner("Fetching data and running backtest — first-time fetches over wide ranges can take a while..."):
                    _run_backtest(code, config)
            except Exception as e:
                st.error(str(e))

    if "metrics" in st.session_state:
        _render_report(config)


if __name__ == "__main__":
    main()
