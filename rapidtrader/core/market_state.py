"""Market state management:
- Handles SPY data caching and market regime detection for the trading system.
- Provides bull/bear market filtering using SPY 200-SMA.
"""

import pandas as pd
from datetime import date, timedelta
from .config import settings
from ..risk.controls import upsert_market_state

def refresh_spy_cache(days: int = 300):
    end_date = date.today()
    start_date = end_date - timedelta(days=days)
    
    from ..data.ingest import refresh_spy_cache as _refresh_spy_cache
    
    try:
        close_prices = _refresh_spy_cache(days)
        
        if close_prices.empty:
            raise RuntimeError(f"No {settings.RT_MARKET_FILTER_SYMBOL} data received")
        
        upsert_market_state(close_prices, settings.RT_MARKET_FILTER_SMA)
        
        return close_prices
        
    except Exception as e:
        raise RuntimeError(f"SPY cache refresh failed: {e}")

def get_market_state(target_date: date) -> dict:
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
            "bull_gate": False
        }

def is_bull_market(target_date: date = None) -> bool:
    if target_date is None:
        from sqlalchemy import text
        from .db import get_engine
        
        eng = get_engine()
        with eng.begin() as conn:
            result = conn.execute(text("""
                SELECT MAX(d) FROM market_state WHERE bull_gate IS NOT NULL
            """)).scalar()
            
        if result is None:
            return False
        target_date = result
    
    market_state = get_market_state(target_date)
    return market_state.get("bull_gate", False)
