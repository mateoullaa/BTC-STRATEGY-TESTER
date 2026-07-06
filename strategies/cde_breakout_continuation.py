"""CDE Crypto: VWAP-band breakout + retest continuation (5m BTC/USDT).

Adapted from a discretionary strategy: multi-timeframe bias (1H EMA50 / 4H
EMA200), a big-body/high-volume breakout of a session VWAP deviation band,
a retest of that band within an expiring window, and entry on a rejection
wick — traded only in the NY AM session (10:00-13:00 ART = 13:00-16:00 UTC),
Monday-Friday, max 1 trade/day, forced flat at session end.

Known simplifications (the generate_signals(df) -> df contract only carries a
single `signal` column, so anything path-dependent has to be pre-resolved
here into an equivalent signal series before the generic backtest_engine
sees it):

- SL/TP/trailing/breakeven are simulated bar-by-bar inside this module
  (_simulate_trade_exit) using OHLC touches — not a real limit-order fill or
  intrabar tick path. The stop level trails to (extreme - 1R) once profit
  reaches 1.5R, which also subsumes moving to breakeven.
- Position sizing is NOT risk-based here. The backtest_engine only accepts a
  single fixed position_size_pct/leverage for the whole run — adjust those in
  the app's sidebar to approximate your real per-trade risk budget; this
  strategy cannot size each trade by its own stop distance.
- No macro news/holiday filter is applied (no data source available) — the
  measured edge does not account for skipping those days.
- VWAP's "session" anchor is assumed to reset daily at 00:00 UTC (the common
  default), not specifically at the NY AM session's own start.
- The source strategy's "SHORT en la banda superior" section appears to be a
  copy/paste of the long section with a typo (breaking below the *upper*
  band). This implementation instead treats the lower band as the short
  breakout level, mirroring the long setup at the upper band.
"""

import pandas as pd

from tools.data_fetcher import fetch_ohlcv

SYMBOL = "BTC/USDT"

# Session: NY AM, 10:00-13:00 ART (UTC-3, no DST) == 13:00-16:00 UTC, Mon-Fri.
SESSION_START_UTC = "13:00"
SESSION_END_UTC = "16:00"

MA_LENGTH = 20
ATR_LENGTH = 14
EMA_FAST_1H = 50
EMA_SLOW_4H = 200
VWAP_BAND_MULT = 1.0

BREAKOUT_VOL_MULT = 1.2
RESET_VOL_MULT = 1.5
RETEST_MIN_BARS = 1
RETEST_MAX_BARS = 6
WICK_REJECTION_MULT = 1.5
SWING_LOOKBACK_BARS = 10
SL_ATR_BUFFER = 0.1

RISK_REWARD = 2.0
BREAKEVEN_R = 1.5
TRAIL_R = 1.5


def _session_vwap_bands(df: pd.DataFrame) -> tuple[pd.Series, pd.Series, pd.Series]:
    session_day = df.index.tz_convert("UTC").normalize()
    typical_price = (df["high"] + df["low"] + df["close"]) / 3
    volume = df["volume"]

    cum_vol = volume.groupby(session_day).cumsum()
    cum_vol_tp = (typical_price * volume).groupby(session_day).cumsum()
    vwap = cum_vol_tp / cum_vol

    dev_sq = (typical_price - vwap) ** 2 * volume
    variance = dev_sq.groupby(session_day).cumsum() / cum_vol
    stdev = variance ** 0.5

    upper = vwap + VWAP_BAND_MULT * stdev
    lower = vwap - VWAP_BAND_MULT * stdev
    return vwap, upper, lower


def _atr(df: pd.DataFrame, length: int = ATR_LENGTH) -> pd.Series:
    prev_close = df["close"].shift(1)
    true_range = pd.concat(
        [
            df["high"] - df["low"],
            (df["high"] - prev_close).abs(),
            (df["low"] - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return true_range.ewm(alpha=1 / length, adjust=False).mean()


def _htf_bias(df: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    start = df.index.min() - pd.Timedelta(days=120)
    end = df.index.max()

    h1 = fetch_ohlcv(SYMBOL, "1h", str(start.date()), str(end.date()))
    h4 = fetch_ohlcv(SYMBOL, "4h", str(start.date()), str(end.date()))

    ema50_1h = h1["close"].ewm(span=EMA_FAST_1H, adjust=False).mean()
    ema200_4h = h4["close"].ewm(span=EMA_SLOW_4H, adjust=False).mean()

    # Shift by 1 bar so the bias reflects the last CLOSED higher-timeframe
    # candle, never the one still forming as of each 5m timestamp.
    above_1h = (h1["close"] > ema50_1h).shift(1)
    above_4h = (h4["close"] > ema200_4h).shift(1)

    above_1h_5m = above_1h.reindex(df.index, method="ffill").fillna(False).astype(bool)
    above_4h_5m = above_4h.reindex(df.index, method="ffill").fillna(False).astype(bool)

    bullish = above_1h_5m & above_4h_5m
    bearish = (~above_1h_5m) & (~above_4h_5m)
    return bullish, bearish


def _in_session_window(index: pd.DatetimeIndex) -> pd.Series:
    utc_index = index.tz_convert("UTC")
    weekday_ok = utc_index.weekday < 5
    start_t = pd.Timestamp(SESSION_START_UTC).time()
    end_t = pd.Timestamp(SESSION_END_UTC).time()
    time_ok = (utc_index.time >= start_t) & (utc_index.time < end_t)
    return pd.Series(weekday_ok & time_ok, index=index)


def _find_retest_entry(df, breakout_iloc, direction, upper, lower, body, body_ma, vol_ma, atr, bullish_bias, bearish_bias):
    band = upper if direction == "long" else lower
    session_end_t = pd.Timestamp(SESSION_END_UTC).time()
    expiry = breakout_iloc + RETEST_MAX_BARS
    hard_cap = min(len(df) - 1, breakout_iloc + RETEST_MAX_BARS + 20)

    j = breakout_iloc + 1
    while j <= expiry and j <= hard_cap:
        if df.index[j].tz_convert("UTC").time() >= session_end_t:
            return None

        bar = df.iloc[j]
        band_j = band.iloc[j]
        bar_body = body.iloc[j]
        last3_body_max = body.iloc[max(0, j - 3):j].max()
        bias_ok = bullish_bias.iloc[j] if direction == "long" else bearish_bias.iloc[j]

        is_reset_candle = (
            bar_body > last3_body_max
            and df["volume"].iloc[j] >= RESET_VOL_MULT * vol_ma.iloc[j]
            and abs(bar["close"] - band_j) <= atr.iloc[j]
            and ((bar["close"] > bar["open"]) if direction == "long" else (bar["close"] < bar["open"]))
        )
        if is_reset_candle:
            expiry = j + RETEST_MAX_BARS

        touched_band = bar["low"] <= band_j <= bar["high"]
        if touched_band and bias_ok:
            if direction == "long":
                wick = min(bar["open"], bar["close"]) - bar["low"]
            else:
                wick = bar["high"] - max(bar["open"], bar["close"])
            rejection = wick >= WICK_REJECTION_MULT * bar_body if bar_body > 0 else wick > 0

            invalidated = (
                (bar["close"] < band_j and bar_body > body_ma.iloc[j] and df["volume"].iloc[j] >= vol_ma.iloc[j])
                if direction == "long"
                else (bar["close"] > band_j and bar_body > body_ma.iloc[j] and df["volume"].iloc[j] >= vol_ma.iloc[j])
            )
            if invalidated:
                return None  # opposite breakout invalidates the whole setup

            if rejection:
                return j

        j += 1
    return None


def _simulate_trade_exit(df: pd.DataFrame, entry_iloc: int, direction: str, atr: pd.Series) -> int:
    entry_price = df["close"].iloc[entry_iloc]
    lookback_start = max(0, entry_iloc - SWING_LOOKBACK_BARS)
    atr_at_entry = atr.iloc[entry_iloc]
    session_end_t = pd.Timestamp(SESSION_END_UTC).time()

    if direction == "long":
        swing = df["low"].iloc[lookback_start:entry_iloc + 1].min()
        risk = entry_price - (swing - SL_ATR_BUFFER * atr_at_entry)
        if risk <= 0:
            risk = atr_at_entry
        tp = entry_price + RISK_REWARD * risk
        stop = entry_price - risk
    else:
        swing = df["high"].iloc[lookback_start:entry_iloc + 1].max()
        risk = (swing + SL_ATR_BUFFER * atr_at_entry) - entry_price
        if risk <= 0:
            risk = atr_at_entry
        tp = entry_price - RISK_REWARD * risk
        stop = entry_price + risk

    trailing_active = False
    extreme = entry_price
    n = len(df)

    for j in range(entry_iloc + 1, n):
        if df.index[j].tz_convert("UTC").time() >= session_end_t:
            return j

        bar = df.iloc[j]
        if direction == "long":
            extreme = max(extreme, bar["high"])
            if not trailing_active and (extreme - entry_price) >= BREAKEVEN_R * risk:
                trailing_active = True
            if trailing_active:
                stop = max(stop, extreme - TRAIL_R * risk)
            if bar["low"] <= stop or bar["high"] >= tp:
                return j
        else:
            extreme = min(extreme, bar["low"])
            if not trailing_active and (entry_price - extreme) >= BREAKEVEN_R * risk:
                trailing_active = True
            if trailing_active:
                stop = min(stop, extreme + TRAIL_R * risk)
            if bar["high"] >= stop or bar["low"] <= tp:
                return j

    return n - 1


def generate_signals(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    signal = pd.Series(0, index=df.index, dtype=int)

    body = (df["close"] - df["open"]).abs()
    body_ma = body.rolling(MA_LENGTH).mean()
    vol_ma = df["volume"].rolling(MA_LENGTH).mean()
    vol_prev3_max = df["volume"].shift(1).rolling(3).max()

    _, upper, lower = _session_vwap_bands(df)
    atr = _atr(df)
    bullish_bias, bearish_bias = _htf_bias(df)
    in_session = _in_session_window(df.index)

    breakout_up = (
        (df["close"] > upper) & (body > body_ma)
        & (df["volume"] >= BREAKOUT_VOL_MULT * vol_ma)
        & (df["volume"] >= vol_prev3_max)
        & in_session & bullish_bias
    )
    breakout_down = (
        (df["close"] < lower) & (body > body_ma)
        & (df["volume"] >= BREAKOUT_VOL_MULT * vol_ma)
        & (df["volume"] >= vol_prev3_max)
        & in_session & bearish_bias
    )

    long_ilocs = [i for i, v in enumerate(breakout_up.to_numpy()) if v]
    short_ilocs = [i for i, v in enumerate(breakout_down.to_numpy()) if v]
    candidates = sorted([(i, "long") for i in long_ilocs] + [(i, "short") for i in short_ilocs])

    utc_dates = df.index.tz_convert("UTC")
    last_trade_day = None
    next_free_iloc = 0

    for breakout_iloc, direction in candidates:
        if breakout_iloc < next_free_iloc:
            continue

        day = utc_dates[breakout_iloc].date()
        if day == last_trade_day:
            continue

        entry_iloc = _find_retest_entry(
            df, breakout_iloc, direction, upper, lower, body, body_ma, vol_ma, atr,
            bullish_bias, bearish_bias,
        )
        if entry_iloc is None:
            continue

        exit_iloc = _simulate_trade_exit(df, entry_iloc, direction, atr)

        signal.iloc[entry_iloc:exit_iloc] = 1 if direction == "long" else -1

        last_trade_day = day
        next_free_iloc = exit_iloc + 1

    df["signal"] = signal
    return df
