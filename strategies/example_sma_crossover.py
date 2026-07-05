"""Example strategy: SMA crossover, used by tests/test_smoke.py.

Implements the required contract: generate_signals(df) -> df with a `signal`
column (1 = long, -1 = short, 0 = flat).
"""

import pandas as pd

FAST_WINDOW = 10
SLOW_WINDOW = 50


def generate_signals(df: pd.DataFrame) -> pd.DataFrame:
    sma_fast = df["close"].rolling(FAST_WINDOW).mean()
    sma_slow = df["close"].rolling(SLOW_WINDOW).mean()

    df = df.copy()
    df["signal"] = 0
    df.loc[sma_fast > sma_slow, "signal"] = 1
    df.loc[sma_fast < sma_slow, "signal"] = -1
    return df
