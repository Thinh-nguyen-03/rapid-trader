"""Signal confirmation logic for RapidTrader strategies.

Implements 2-of-3 confirmation window to reduce false signals
by requiring multiple confirmations within a time window.
"""

import pandas as pd


def confirm(signal_bool: pd.Series, window: int, min_count: int) -> pd.Series:
    """Apply confirmation logic to a boolean signal series.
    
    Args:
        signal_bool: Boolean series of raw signals (True = signal present)
        window: Number of periods to look back for confirmation
        min_count: Minimum number of confirmations required in window
        
    Returns:
        Boolean series where True indicates confirmed signal
        
    Examples:
        >>> signals = pd.Series([False, True, True, False, True])
        >>> confirm(signals, window=3, min_count=2)
        # Returns series where only periods with 2+ signals in 3-day window are True
    """
    # Convert boolean to integer (True=1, False=0)
    signal_int = signal_bool.astype(int)
    
    # Calculate rolling sum of signals
    strength = signal_int.rolling(window, min_periods=1).sum()
    
    # Return True where strength meets minimum threshold
    return strength >= min_count
