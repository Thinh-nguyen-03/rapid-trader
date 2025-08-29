"""SMA Crossover Strategy for RapidTrader.

Implements Simple Moving Average crossover strategy with confirmation:
- Buy signals when fast SMA > slow SMA (uptrend)
- Sell signals when fast SMA < slow SMA (downtrend)
- Uses confirmation logic to reduce whipsaws
"""

import pandas as pd
from ..indicators.core import sma
from .confirmation import confirm


def sma_crossover(
    df: pd.DataFrame, 
    fast: int = 20, 
    slow: int = 100, 
    confirm_days: int = 2
) -> pd.DataFrame:
    """Generate SMA crossover signals with confirmation.
    
    Args:
        df: DataFrame with OHLCV data (requires 'close' column)
        fast: Fast SMA period (default 20)
        slow: Slow SMA period (default 100)
        confirm_days: Days of confirmation required (default 2)
        
    Returns:
        DataFrame with columns:
        - fast: Fast SMA values
        - slow: Slow SMA values
        - signal: Final signal ('buy', 'sell', or 'hold')
        
    Strategy Logic:
        - Buy when fast SMA > slow SMA for confirm_days consecutive days
        - Sell when fast SMA < slow SMA for confirm_days consecutive days
        - Requires confirmation to avoid false signals from brief crossovers
    """
    # Initialize output DataFrame with same index as input
    out = pd.DataFrame(index=df.index)
    
    # Calculate moving averages
    out["fast"] = sma(df["close"], fast)
    out["slow"] = sma(df["close"], slow)
    
    # Generate raw crossover signals
    up_trend = out["fast"] > out["slow"]  # Fast above slow = bullish
    down_trend = out["fast"] < out["slow"]  # Fast below slow = bearish
    
    # Apply confirmation logic
    # Both buy and sell signals require confirmation to reduce whipsaws
    confirmed_up = confirm(up_trend, confirm_days, confirm_days)
    confirmed_down = confirm(down_trend, confirm_days, confirm_days)
    
    # Generate final signals
    out["signal"] = "hold"
    out.loc[confirmed_up, "signal"] = "buy"
    out.loc[confirmed_down, "signal"] = "sell"
    
    return out
