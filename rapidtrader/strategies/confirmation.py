"""Signal confirmation logic for RapidTrader strategies."""

import pandas as pd


def confirm(signal_bool: pd.Series, window: int, min_count: int) -> pd.Series:
    """Apply confirmation logic to a boolean signal series.

    Args:
        signal_bool: Boolean series of raw signals (True = signal present)
        window: Number of periods to look back for confirmation
        min_count: Minimum number of confirmations required in window

    Returns:
        Boolean series where True indicates confirmed signal
    """
    signal_int = signal_bool.astype(int)
    strength = signal_int.rolling(window, min_periods=1).sum()
    return strength >= min_count
