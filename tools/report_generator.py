"""Builds the exportable PDF report from computed metrics and the equity curve.

Contract:
    generate_pdf_report(metrics: dict, equity_curve: pd.Series, output_path: str) -> str
        Writes a PDF to output_path (metrics table + equity curve chart) and
        returns the path.

Status: not yet implemented. Built by the Builder role per roles/builder.md.
"""

import pandas as pd


def generate_pdf_report(metrics: dict, equity_curve: pd.Series, output_path: str) -> str:
    raise NotImplementedError
