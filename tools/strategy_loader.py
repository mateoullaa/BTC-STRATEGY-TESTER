"""Loads and validates a user-provided strategy against its required contract.

Contract the loaded strategy module must expose:
    generate_signals(df: pd.DataFrame) -> pd.DataFrame
        Receives the OHLCV DataFrame (columns: open, high, low, close, volume)
        and returns the same DataFrame with an added `signal` column:
        1 = enter/hold long, -1 = enter/hold short, 0 = flat.

Accepts either a file path (uploaded .py) or a source string (pasted code).

Status: not yet implemented. Built by the Builder role per roles/builder.md.
"""

from types import ModuleType


def load_strategy(source: str, from_path: bool = False) -> ModuleType:
    raise NotImplementedError


def validate_signals(df) -> None:
    """Raise if the `signal` column is missing or contains values outside {1, -1, 0}."""
    raise NotImplementedError
