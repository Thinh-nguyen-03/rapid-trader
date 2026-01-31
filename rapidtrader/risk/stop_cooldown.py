"""Stop loss management and cooldown tracking for RapidTrader."""

from datetime import date, timedelta
from sqlalchemy import text
from ..core.db import get_engine


def stop_cooldown_active(symbol: str, current_date: date, cooldown_days: int = 1) -> bool:
    """Check if a symbol is in cooldown period after stop loss."""
    eng = get_engine()
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
    """Record a stop loss event in the database."""
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
