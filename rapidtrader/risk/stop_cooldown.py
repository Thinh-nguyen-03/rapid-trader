"""Stop loss management and cooldown tracking for RapidTrader.

Implements stop loss event tracking and cooldown periods to prevent
immediate re-entry after stops are hit.
"""

from datetime import date, timedelta
from sqlalchemy import text
from ..core.db import get_engine


def stop_cooldown_active(symbol: str, current_date: date, cooldown_days: int = 1) -> bool:
    """Check if a symbol is in cooldown period after stop loss.
    
    Args:
        symbol: Stock symbol to check
        current_date: Current trading date
        cooldown_days: Number of days to wait after stop (default 1)
        
    Returns:
        True if symbol is in cooldown period (can't enter new positions)
        
    Logic:
        - Looks back cooldown_days from current_date
        - Returns True if any STOP_HIT events found in that period
        - Prevents immediate re-entry after stop losses
        
    Examples:
        >>> stop_cooldown_active("AAPL", date(2024, 1, 15), 1)
        True  # AAPL had stop hit on 2024-01-14, still in 1-day cooldown
    """
    eng = get_engine()
    
    # Calculate start of cooldown period
    cooldown_start = current_date - timedelta(days=cooldown_days)
    
    with eng.begin() as conn:
        result = conn.execute(text("""
            SELECT 1 FROM symbol_events
            WHERE symbol = :symbol 
                AND event = 'STOP_HIT' 
                AND d >= :start_date 
                AND d < :current_date
            LIMIT 1
        """), {
            "symbol": symbol,
            "start_date": cooldown_start,
            "current_date": current_date
        }).first()
    
    return result is not None


def record_stop_event(symbol: str, event_date: date, stop_price: float = None):
    """Record a stop loss event in the database.
    
    Args:
        symbol: Stock symbol that hit stop
        event_date: Date when stop was triggered
        stop_price: Price at which stop was hit (optional)
        
    Records STOP_HIT event in symbol_events table for cooldown tracking.
    """
    eng = get_engine()
    
    details = {"stop_price": stop_price} if stop_price is not None else None
    
    with eng.begin() as conn:
        conn.execute(text("""
            INSERT INTO symbol_events (symbol, d, event, details)
            VALUES (:symbol, :date, 'STOP_HIT', :details)
            ON CONFLICT (symbol, d, event) DO NOTHING
        """), {
            "symbol": symbol,
            "date": event_date,
            "details": details
        })
