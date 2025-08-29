"""End-of-Day Data Ingestion Job for RapidTrader.

Automated job to download daily OHLCV data for all symbols in the universe
and refresh the SPY market state cache for trading decisions.
"""

import argparse
from sqlalchemy import text
from ..core.db import get_engine
from ..data.ingest import ingest_symbols
from ..core.market_state import refresh_spy_cache


def get_active_symbols() -> list[str]:
    """Get list of active symbols from database.
    
    Returns:
        List of active symbol strings
    """
    eng = get_engine()
    
    with eng.begin() as conn:
        result = conn.execute(text("""
            SELECT symbol FROM symbols 
            WHERE is_active = true 
            ORDER BY symbol
        """)).all()
    
    return [row[0] for row in result]


def main():
    """Main EOD ingestion job entry point."""
    parser = argparse.ArgumentParser(
        description="RapidTrader End-of-Day Data Ingestion Job"
    )
    parser.add_argument(
        "--days", 
        type=int, 
        default=300,
        help="Number of days of historical data to fetch (default: 300)"
    )
    parser.add_argument(
        "--symbols-only",
        action="store_true",
        help="Only ingest symbol data, skip SPY cache refresh"
    )
    parser.add_argument(
        "--spy-only",
        action="store_true", 
        help="Only refresh SPY cache, skip symbol data"
    )
    
    args = parser.parse_args()
    
    try:
        print("Starting EOD data ingestion job...")
        
        if not args.spy_only:
            # Get active symbols from database
            symbols = get_active_symbols()
            print(f"Found {len(symbols)} active symbols to update")
            
            if symbols:
                # Ingest OHLCV data for all symbols
                print("Ingesting symbol data...")
                ingest_symbols(symbols, days=args.days)
                print("Symbol data ingestion complete")
            else:
                print("Warning: No active symbols found in database")
        
        if not args.symbols_only:
            # Refresh SPY market state cache
            print("Refreshing SPY market state cache...")
            close_prices = refresh_spy_cache(days=args.days)
            print(f"SPY cache refreshed with {len(close_prices)} days of data")
        
        print("EOD data ingestion job completed successfully")
        return 0
        
    except Exception as e:
        print(f"EOD ingestion job failed: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
