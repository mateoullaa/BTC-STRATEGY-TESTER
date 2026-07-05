"""Fetches historical BTC/USDT OHLCV candles from the Binance public API.

Contract:
    fetch_ohlcv(symbol: str, timeframe: str, start: str, end: str) -> pd.DataFrame
        Returns a DataFrame indexed by UTC timestamp with columns:
        open, high, low, close, volume

Results are cached locally (data_cache/) to avoid redundant API calls across runs.
No API key required — uses Binance's public klines endpoint.
"""

import time
from pathlib import Path

import pandas as pd
import requests

BINANCE_KLINES_URL = "https://api.binance.com/api/v3/klines"
CACHE_DIR = Path(__file__).resolve().parent.parent / "data_cache"
MAX_CANDLES_PER_REQUEST = 1000

INTERVAL_MS = {
    "1m": 60_000,
    "5m": 5 * 60_000,
    "15m": 15 * 60_000,
    "1h": 60 * 60_000,
    "4h": 4 * 60 * 60_000,
    "1d": 24 * 60 * 60_000,
}

OHLCV_COLUMNS = ["open", "high", "low", "close", "volume"]


def _normalize_symbol(symbol: str) -> str:
    return symbol.replace("/", "").upper()


def _cache_path(symbol: str, timeframe: str) -> Path:
    return CACHE_DIR / f"{_normalize_symbol(symbol)}_{timeframe}.parquet"


def _to_ms(ts) -> int:
    ts = pd.Timestamp(ts)
    ts = ts.tz_localize("UTC") if ts.tzinfo is None else ts.tz_convert("UTC")
    return int(ts.timestamp() * 1000)


def _request_klines(symbol: str, timeframe: str, start_ms: int, end_ms: int) -> list:
    params = {
        "symbol": symbol,
        "interval": timeframe,
        "startTime": start_ms,
        "endTime": end_ms,
        "limit": MAX_CANDLES_PER_REQUEST,
    }
    for attempt in range(5):
        response = requests.get(BINANCE_KLINES_URL, params=params, timeout=10)
        if response.status_code in (429, 418):
            wait = float(response.headers.get("Retry-After", 1.0))
            time.sleep(wait)
            continue
        response.raise_for_status()
        return response.json()
    response.raise_for_status()
    return []


def _fetch_range(symbol: str, timeframe: str, start_ms: int, end_ms: int) -> pd.DataFrame:
    if timeframe not in INTERVAL_MS:
        raise ValueError(f"Unsupported timeframe: {timeframe!r}. Use one of {list(INTERVAL_MS)}.")

    interval_ms = INTERVAL_MS[timeframe]
    now_ms = int(time.time() * 1000)
    cursor = start_ms
    rows = []

    while cursor < end_ms:
        batch = _request_klines(symbol, timeframe, cursor, end_ms)
        if not batch:
            break

        rows.extend(batch)
        last_open_time = batch[-1][0]
        cursor = last_open_time + interval_ms

        if len(batch) < MAX_CANDLES_PER_REQUEST:
            break
        time.sleep(0.2)

    if not rows:
        return pd.DataFrame(columns=OHLCV_COLUMNS, index=pd.DatetimeIndex([], tz="UTC"))

    df = pd.DataFrame(
        rows,
        columns=[
            "open_time", "open", "high", "low", "close", "volume",
            "close_time", "quote_asset_volume", "num_trades",
            "taker_buy_base", "taker_buy_quote", "ignore",
        ],
    )
    df = df.drop_duplicates(subset="open_time")
    df = df[df["close_time"] < now_ms]  # drop a still-forming trailing candle

    df.index = pd.to_datetime(df["open_time"], unit="ms", utc=True)
    df = df[OHLCV_COLUMNS].astype(float)
    return df.sort_index()


def fetch_ohlcv(symbol: str, timeframe: str, start: str, end: str) -> pd.DataFrame:
    start_ts = pd.Timestamp(start, tz="UTC")
    end_ts = pd.Timestamp(end, tz="UTC")
    if start_ts >= end_ts:
        raise ValueError(f"start ({start}) must be before end ({end})")

    symbol = _normalize_symbol(symbol)
    cache_file = _cache_path(symbol, timeframe)
    cached = pd.read_parquet(cache_file) if cache_file.exists() else None

    fresh_parts = []
    if cached is None or cached.empty:
        fresh_parts.append(_fetch_range(symbol, timeframe, _to_ms(start_ts), _to_ms(end_ts)))
    else:
        cached_min, cached_max = cached.index.min(), cached.index.max()
        if start_ts < cached_min:
            fresh_parts.append(_fetch_range(symbol, timeframe, _to_ms(start_ts), _to_ms(cached_min)))
        if end_ts > cached_max:
            fresh_parts.append(_fetch_range(symbol, timeframe, _to_ms(cached_max), _to_ms(end_ts)))

    combined = pd.concat([cached] + fresh_parts) if cached is not None else pd.concat(fresh_parts)
    combined = combined[~combined.index.duplicated(keep="last")].sort_index()

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    combined.to_parquet(cache_file)

    return combined.loc[start_ts:end_ts]
