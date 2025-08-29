"""Market state management for RapidTrader.

Handles SPY data caching and market regime detection for the trading system.
Provides bull/bear market filtering using SPY 200-SMA.
"""

import pandas as pd
from datetime import date, timedelta
from .config import settings
from ..risk.controls import upsert_market_state


def refresh_spy_cache(days: int = 300):
    """Refresh SPY market state cache using Polygon.io data.
    
    Args:
        days: Number of days of SPY history to cache (default 300)
        
    Returns:
        pandas.Series: SPY closing prices with date index
        
    Updates market_state table with:
        - SPY closing prices
        - 200-day SMA values  
        - Bull/bear market gates
        
    Raises:
        RuntimeError: If SPY data download fails
    """
    end_date = date.today()
    start_date = end_date - timedelta(days=days)
    
    # Import here to avoid circular imports and use existing data pipeline
    from ..data.ingest import refresh_spy_cache as _refresh_spy_cache
    
    try:
        # Get SPY data using existing data pipeline (returns close prices directly)
        close_prices = _refresh_spy_cache(days)
        
        if close_prices.empty:
            raise RuntimeError(f"No {settings.RT_MARKET_FILTER_SYMBOL} data received")
        
        # Update market state cache
        upsert_market_state(close_prices, settings.RT_MARKET_FILTER_SMA)
        
        return close_prices
        
    except Exception as e:
        raise RuntimeError(f"SPY cache refresh failed: {e}")


def get_market_state(target_date: date) -> dict:
    """Get cached market state for a specific date.
    
    Args:
        target_date: Date to query market state for
        
    Returns:
        dict with keys:
        - bull_gate: Boolean indicating bullish market
        - spy_close: SPY closing price
        - spy_sma200: 200-day SMA value
        - date: Date of the data
        
    Returns None values if no data found for the date.
    """
    from sqlalchemy import text
    from .db import get_engine
    
    eng = get_engine()
    
    with eng.begin() as conn:
        result = conn.execute(text("""
            SELECT d, spy_close, spy_sma200, bull_gate
            FROM market_state 
            WHERE d = :date
        """), {"date": target_date}).first()
    
    if result:
        return {
            "date": result[0],
            "spy_close": result[1],
            "spy_sma200": result[2],
            "bull_gate": result[3]
        }
    else:
        return {
            "date": target_date,
            "spy_close": None,
            "spy_sma200": None,
            "bull_gate": False  # Default to bear market if no data
        }


def is_bull_market(target_date: date = None) -> bool:
    """Check if market is in bull regime for trading decisions.
    
    Args:
        target_date: Date to check (defaults to latest available)
        
    Returns:
        True if market is bullish (allow new long entries)
        False if bearish or no data (block new entries)
    """
    if target_date is None:
        # Get latest date from market_state
        from sqlalchemy import text
        from .db import get_engine
        
        eng = get_engine()
        with eng.begin() as conn:
            result = conn.execute(text("""
                SELECT MAX(d) FROM market_state WHERE bull_gate IS NOT NULL
            """)).scalar()
            
        if result is None:
            return False  # No data, default to bear market
        target_date = result
    
    market_state = get_market_state(target_date)
    return market_state.get("bull_gate", False)
