"""Fetches historical BTC/USDT OHLCV candles from the Binance public API.

Contract:
    fetch_ohlcv(symbol: str, timeframe: str, start: str, end: str) -> pd.DataFrame
        Returns a DataFrame indexed by UTC timestamp with columns:
        open, high, low, close, volume

Results are cached locally (data_cache/) to avoid redundant API calls across runs.
No API key required — uses Binance's public klines endpoint.

Status: not yet implemented. Built by the Builder role per roles/builder.md.
"""

import pandas as pd


def fetch_ohlcv(symbol: str, timeframe: str, start: str, end: str) -> pd.DataFrame:
    raise NotImplementedError
