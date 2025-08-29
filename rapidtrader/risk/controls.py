"""Risk control mechanisms for RapidTrader.

Implements various risk controls:
1. Market filter using SPY 200-SMA bull/bear detection
2. Sector exposure limits
3. Market state caching for performance
"""

import pandas as pd
from sqlalchemy import text
from ..core.db import get_engine
from ..indicators.core import sma


def market_ok(spy_close: pd.Series, n: int = 200) -> pd.Series:
    """Determine if market conditions are favorable for new entries.
    
    Args:
        spy_close: SPY closing prices as pandas Series
        n: SMA period for market filter (default 200)
        
    Returns:
        Boolean series where True indicates bullish market (SPY >= SMA200)
        
    Market Filter Logic:
        - Bull market: SPY closing price >= 200-day SMA
        - Bear market: SPY closing price < 200-day SMA
        - No new long entries during bear markets
    """
    spy_sma = sma(spy_close, n)
    return spy_close >= spy_sma


def upsert_market_state(spy_close: pd.Series, n: int = 200):
    """Update market state cache in database.
    
    Args:
        spy_close: SPY closing prices as pandas Series
        n: SMA period for calculation (default 200)
        
    Updates market_state table with:
        - spy_close: SPY closing price
        - spy_sma200: 200-day SMA value
        - bull_gate: Boolean indicating bullish market
    """
    eng = get_engine()
    spy_sma = sma(spy_close, n)
    bull_gate = market_ok(spy_close, n)
    
    with eng.begin() as conn:
        for dt, close_px in spy_close.dropna().items():
            sma_val = spy_sma.loc[dt] if pd.notna(spy_sma.loc[dt]) else None
            gate_val = bool(bull_gate.loc[dt]) if pd.notna(bull_gate.loc[dt]) else False
            
            conn.execute(text("""
                INSERT INTO market_state (d, spy_close, spy_sma200, bull_gate)
                VALUES (:d, :px, :sma, :gate)
                ON CONFLICT (d) DO UPDATE SET 
                    spy_close = :px, 
                    spy_sma200 = :sma, 
                    bull_gate = :gate
            """), {
                "d": dt.date(), 
                "px": float(close_px), 
                "sma": float(sma_val) if sma_val is not None else None,
                "gate": gate_val
            })


def sector_exposure_ok(
    current_sector_value: float, 
    portfolio_value: float, 
    candidate_value: float, 
    max_pct: float = 0.30
) -> bool:
    """Check if adding a position would violate sector exposure limits.
    
    Args:
        current_sector_value: Current dollar value invested in this sector
        portfolio_value: Total portfolio value
        candidate_value: Dollar value of proposed new position
        max_pct: Maximum sector exposure as fraction (default 0.30 = 30%)
        
    Returns:
        True if the new position would keep sector exposure within limits
        
    Examples:
        >>> sector_exposure_ok(25000, 100000, 10000, 0.30)
        False  # (25k + 10k) / 100k = 35% > 30% limit
        
        >>> sector_exposure_ok(20000, 100000, 5000, 0.30) 
        True   # (20k + 5k) / 100k = 25% < 30% limit
    """
    # Avoid division by zero
    portfolio_value = max(1e-9, portfolio_value)
    
    # Calculate total sector exposure after adding candidate position
    total_sector_value = current_sector_value + candidate_value
    sector_exposure_pct = total_sector_value / portfolio_value
    
    return sector_exposure_pct <= max_pct
