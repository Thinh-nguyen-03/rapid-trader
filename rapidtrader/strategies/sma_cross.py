"""SMA Crossover Strategy for RapidTrader."""

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
        DataFrame with columns: fast, slow, signal
    """
    out = pd.DataFrame(index=df.index)

    out["fast"] = sma(df["close"], fast)
    out["slow"] = sma(df["close"], slow)

    up_trend = out["fast"] > out["slow"]
    down_trend = out["fast"] < out["slow"]

    confirmed_up = confirm(up_trend, confirm_days, confirm_days)
    confirmed_down = confirm(down_trend, confirm_days, confirm_days)

    out["signal"] = "hold"
    out.loc[confirmed_up, "signal"] = "buy"
    out.loc[confirmed_down, "signal"] = "sell"

    return out
