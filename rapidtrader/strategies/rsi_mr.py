"""RSI Mean-Reversion Strategy for RapidTrader.

Implements RSI-based mean-reversion strategy with confirmation logic:
- Buy signals when RSI < 30 (oversold condition)
- Sell signals when RSI >= 55 (exit condition)
- Uses 2-of-3 confirmation window to reduce false signals
"""

import pandas as pd
from ..indicators.core import rsi_wilder
from .confirmation import confirm


def rsi_mean_reversion(
    df: pd.DataFrame, 
    buy_rsi: float = 30.0, 
    sell_rsi: float = 55.0, 
    window: int = 3, 
    min_count: int = 2
) -> pd.DataFrame:
    """Generate RSI mean-reversion signals with confirmation.
    
    Args:
        df: DataFrame with OHLCV data (requires 'close' column)
        buy_rsi: RSI threshold for buy signals (default 30.0)
        sell_rsi: RSI threshold for sell signals (default 55.0)
        window: Confirmation window in days (default 3)
        min_count: Minimum confirmations required (default 2)
        
    Returns:
        DataFrame with columns:
        - rsi: Calculated RSI values
        - buy: Boolean buy signals (with confirmation)
        - sell: Boolean sell signals (raw, no confirmation needed for exits)
        - signal: Final signal ('buy', 'sell', or 'hold')
        
    Strategy Logic:
        - RSI < buy_rsi triggers raw buy signal
        - Confirmation logic requires min_count buy signals within window
        - RSI >= sell_rsi triggers immediate sell signal (exits don't need confirmation)
        - Signal priority: sell > buy > hold
    """
    # Initialize output DataFrame with same index as input
    out = pd.DataFrame(index=df.index)
    
    # Calculate RSI using Wilder's method (14-period default)
    out["rsi"] = rsi_wilder(df["close"], window=14)
    
    # Generate raw signals
    buy_raw = out["rsi"] < buy_rsi
    sell_raw = out["rsi"] >= sell_rsi
    
    # Apply confirmation to buy signals only
    # Exits (sells) don't need confirmation for faster risk management
    out["buy"] = confirm(buy_raw, window, min_count)
    out["sell"] = sell_raw
    
    # Determine final signal with priority: sell > buy > hold
    out["signal"] = "hold"
    out.loc[out["buy"], "signal"] = "buy"
    out.loc[out["sell"], "signal"] = "sell"  # Sells override buys
    
    return out
