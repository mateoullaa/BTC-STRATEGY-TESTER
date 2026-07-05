"""Loads and validates a user-provided strategy against its required contract.

Contract the loaded strategy module must expose:
    generate_signals(df: pd.DataFrame) -> pd.DataFrame
        Receives the OHLCV DataFrame (columns: open, high, low, close, volume)
        and returns the same DataFrame with an added `signal` column:
        1 = enter/hold long, -1 = enter/hold short, 0 = flat.

Accepts either a file path (uploaded .py) or a source string (pasted code).
"""

import importlib.util
import uuid
from types import ModuleType


def load_strategy(source: str, from_path: bool = False) -> ModuleType:
    module_name = f"user_strategy_{uuid.uuid4().hex}"

    try:
        if from_path:
            spec = importlib.util.spec_from_file_location(module_name, source)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
        else:
            module = ModuleType(module_name)
            exec(compile(source, "<pasted_strategy>", "exec"), module.__dict__)
    except Exception as e:
        raise ValueError(f"Failed to load strategy: {e}") from e

    if not hasattr(module, "generate_signals") or not callable(module.generate_signals):
        raise ValueError("Strategy must define a callable generate_signals(df) function.")

    return module


def validate_signals(df) -> None:
    if "signal" not in df.columns:
        raise ValueError("Strategy output is missing the required 'signal' column.")

    if df["signal"].isna().any():
        raise ValueError("'signal' column contains NaN values.")

    valid_values = {1, -1, 0}
    offending = set(df["signal"].unique()) - valid_values
    if offending:
        raise ValueError(
            f"'signal' column must only contain values from {valid_values}, "
            f"found invalid values: {sorted(offending)}"
        )
