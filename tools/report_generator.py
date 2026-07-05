"""Builds the exportable PDF report from computed metrics and the equity curve.

Contract:
    generate_pdf_report(metrics: dict, equity_curve: pd.Series, output_path: str) -> str
        Writes a PDF to output_path (metrics table + equity curve chart) and
        returns the path.

The chart is rendered via matplotlib to an in-memory PNG before being embedded
(kept separate from the interactive Plotly chart used in the Streamlit app —
avoids a plotly+kaleido native dependency for this one static image).
"""

import io
from pathlib import Path

import matplotlib
import pandas as pd
from fpdf import FPDF, XPos, YPos

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

METRIC_LABELS = {
    "expectancy": "Expectancy",
    "win_rate": "Win Rate",
    "profit_factor": "Profit Factor",
    "total_return_pct": "Total Return (%)",
    "total_return_abs": "Total Return ($)",
    "max_drawdown_pct": "Max Drawdown (%)",
    "max_drawdown_duration": "Max Drawdown Duration",
    "sharpe_ratio": "Sharpe Ratio",
    "sortino_ratio": "Sortino Ratio",
    "num_trades": "Number of Trades",
    "avg_win": "Average Win ($)",
    "avg_loss": "Average Loss ($)",
    "cagr": "CAGR",
}

METRIC_FORMATTERS = {
    "expectancy": lambda v: f"${v:,.2f}",
    "win_rate": lambda v: f"{v:.2%}",
    "profit_factor": lambda v: "inf" if v == float("inf") else f"{v:.2f}",
    "total_return_pct": lambda v: f"{v:.2%}",
    "total_return_abs": lambda v: f"${v:,.2f}",
    "max_drawdown_pct": lambda v: f"{v:.2f}%",
    "max_drawdown_duration": lambda v: f"{v:.1f} days",
    "sharpe_ratio": lambda v: f"{v:.2f}",
    "sortino_ratio": lambda v: f"{v:.2f}",
    "num_trades": lambda v: f"{v:d}",
    "avg_win": lambda v: f"${v:,.2f}",
    "avg_loss": lambda v: f"${v:,.2f}",
    "cagr": lambda v: f"{v:.2%}",
}


def _format_metric(key: str, value) -> str:
    formatter = METRIC_FORMATTERS.get(key)
    if formatter is None:
        return str(value)
    try:
        return formatter(value)
    except (ValueError, TypeError):
        return str(value)


def _render_equity_chart(equity_curve: pd.Series) -> io.BytesIO:
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(equity_curve.index, equity_curve.values)
    ax.set_title("Equity Curve")
    ax.set_xlabel("Date")
    ax.set_ylabel("Equity")
    ax.grid(True)
    fig.autofmt_xdate()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf


def generate_pdf_report(metrics: dict, equity_curve: pd.Series, output_path: str) -> str:
    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "BTC/USDT Strategy Backtest Report", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(4)

    pdf.set_font("Helvetica", "", 11)
    label_width, value_width, row_height = 90, 90, 8
    for key, value in metrics.items():
        label = METRIC_LABELS.get(key, key.replace("_", " ").title())
        pdf.cell(label_width, row_height, label, border=1)
        pdf.cell(
            value_width, row_height, _format_metric(key, value), border=1,
            new_x=XPos.LMARGIN, new_y=YPos.NEXT,
        )

    pdf.ln(6)
    chart_buf = _render_equity_chart(equity_curve)
    pdf.image(chart_buf, x=10, w=190)

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(output_path))

    return str(output_path)
