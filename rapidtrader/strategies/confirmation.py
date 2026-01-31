"""Signal confirmation logic for RapidTrader strategies."""

import pandas as pd


def confirm(signal_bool: pd.Series, window: int, min_count: int) -> pd.Series:
    """Apply confirmation logic to a boolean signal series."""
    signal_int = signal_bool.astype(int)
    strength = signal_int.rolling(window, min_periods=1).sum()
    return strength >= min_count
