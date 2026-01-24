"""End-of-Day Data Ingestion Job for RapidTrader.

Automated job to download daily OHLCV data for all symbols in the universe
and refresh the SPY market state cache for trading decisions.
"""

import argparse
from pathlib import Path
from sqlalchemy import text
from ..core.db import get_engine
from ..data.ingest import ingest_symbols
from ..core.market_state import refresh_spy_cache
from ..core.logging_config import setup_logging, get_logger
from ..core.config import settings
from datetime import date

logger = get_logger(__name__)


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
    # Parallel processing is always used - no need for flags
    parser.add_argument(
        "--max-workers",
        type=int,
        default=10,
        help="Maximum concurrent API requests (default: 10)"
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        default=True,
        help="Skip symbols that already have data for today (default: enabled)"
    )
    parser.add_argument(
        "--force-all",
        action="store_true",
        help="Force ingestion for all symbols, ignore existing data"
    )
    
    args = parser.parse_args()

    # Initialize logging
    setup_logging(
        log_level=settings.RT_LOG_LEVEL,
        json_logs=settings.RT_LOG_JSON,
        log_file=Path(settings.RT_LOG_FILE) if settings.RT_LOG_FILE else None
    )

    try:
        logger.info("job_started", job="eod_ingest")

        if not args.spy_only:
            symbols = get_active_symbols()
            logger.info("found_active_symbols", count=len(symbols))

            if symbols:
                skip_existing = args.skip_existing and not args.force_all
                logger.info("ingestion_config", parallel=True, skip_existing=skip_existing)

                ingest_symbols(
                    symbols,
                    days=args.days,
                    target_date=date.today(),
                    skip_existing=skip_existing,
                    max_workers=args.max_workers
                )

                logger.info("symbol_ingestion_complete")
            else:
                logger.warning("no_active_symbols")

        if not args.symbols_only:
            logger.info("refreshing_spy_cache")
            close_prices = refresh_spy_cache(days=args.days)
            logger.info("spy_cache_refreshed", days=len(close_prices))

        logger.info("job_completed", job="eod_ingest")
        return 0

    except Exception as e:
        logger.exception("job_failed", job="eod_ingest", error=str(e))
        return 1


if __name__ == "__main__":
    exit(main())
