"""RSI Mean-Reversion Strategy for RapidTrader."""

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
        DataFrame with columns: rsi, buy, sell, signal
    """
    out = pd.DataFrame(index=df.index)

    out["rsi"] = rsi_wilder(df["close"], window=14)

    buy_raw = out["rsi"] < buy_rsi
    sell_raw = out["rsi"] >= sell_rsi

    out["buy"] = confirm(buy_raw, window, min_count)
    out["sell"] = sell_raw

    out["signal"] = "hold"
    out.loc[out["buy"], "signal"] = "buy"
    out.loc[out["sell"], "signal"] = "sell"

    return out
