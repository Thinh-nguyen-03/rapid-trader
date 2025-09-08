import sys
import os
import argparse
import time
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rapidtrader.core.db import get_engine
from rapidtrader.core.config import settings
from rapidtrader.data.sp500_api import get_sp500_symbols, map_sector_name, PolygonClient
from sqlalchemy import text
from dotenv import load_dotenv

load_dotenv()

def update_sic_database():
    try:
        from scripts.rebuild_sic_database import main as rebuild_sic_main
        
        print("INFO: Rebuilding SIC codes database from SEC website")
        result = rebuild_sic_main()
        
        if result == 0:
            print("SUCCESS: SIC database updated successfully")
            return True
        else:
            print("ERROR: SIC database update failed")
            return False
            
    except Exception as e:
        print(f"ERROR: Failed to update SIC database: {e}")
        return False

def update_symbols_table(clear_existing: bool = False):
    try:
        print("INFO: Fetching S&P 500 symbols from Polygon.io")
        symbols = get_sp500_symbols()
        print(f"INFO: Retrieved {len(symbols)} symbols")
        
        eng = get_engine()
        
        with eng.begin() as conn:
            if clear_existing:
                print("INFO: Clearing existing symbols...")
                conn.execute(text("DELETE FROM symbols"))
            
            print("INFO: Updating symbols table...")
            for symbol, sector in symbols:
                clean_sector = map_sector_name(sector)
                
                # Escape single quotes in sector name
                clean_sector_escaped = clean_sector.replace("'", "''")
                
                conn.execute(text(f"""
                    INSERT INTO symbols (symbol, sector, is_active) 
                    VALUES ('{symbol}', '{clean_sector_escaped}', true)
                    ON CONFLICT (symbol) DO UPDATE SET 
                        sector = '{clean_sector_escaped}', 
                        is_active = true
                """))
            
            total_count = conn.execute(text("SELECT COUNT(*) FROM symbols WHERE is_active = true")).scalar()
            
        print(f"SUCCESS: Updated symbols table with {total_count} active symbols")
        
        # Automatically clean up orphaned symbols from sector_cache
        print("INFO: Cleaning up orphaned symbols from sector_cache...")
        cleanup_sector_cache()
        
        return True
        
    except Exception as e:
        print(f"ERROR: Failed to update symbols table: {e}")
        return False

def cleanup_sector_cache():
    """Remove symbols from sector_cache that are not in the active symbols table."""
    try:
        eng = get_engine()
        with eng.begin() as conn:
            # Count symbols to be removed
            orphaned_count = conn.execute(text("""
                SELECT COUNT(*) 
                FROM sector_cache 
                WHERE symbol NOT IN (SELECT symbol FROM symbols WHERE is_active = true)
            """)).scalar()
            
            if orphaned_count > 0:
                print(f"INFO: Removing {orphaned_count} orphaned symbols from sector_cache...")
                
                # Remove orphaned symbols
                conn.execute(text("""
                    DELETE FROM sector_cache 
                    WHERE symbol NOT IN (SELECT symbol FROM symbols WHERE is_active = true)
                """))
                
                print(f"SUCCESS: Cleaned up {orphaned_count} orphaned symbols from sector_cache")
            else:
                print("INFO: No orphaned symbols found in sector_cache")
            
            return True
            
    except Exception as e:
        print(f"ERROR: Failed to cleanup sector_cache: {e}")
        return False

def update_sector_cache(clear_existing: bool = False):
    try:
        eng = get_engine()
        with eng.begin() as conn:
            if clear_existing:
                print("INFO: Clearing existing sector cache...")
                conn.execute(text("DELETE FROM sector_cache"))
            
            result = conn.execute(text("""
                SELECT symbol 
                FROM symbols 
                WHERE is_active = true 
                ORDER BY symbol
            """)).fetchall()
            
            symbols = [row[0] for row in result]
            
        if not symbols:
            print("WARNING: No symbols found to refresh")
            return False
        
        print(f"INFO: Refreshing sector data for {len(symbols)} symbols...")
        
        client = PolygonClient(settings.RT_POLYGON_API_KEY)
        
        successful_updates = 0
        failed_updates = 0
        batch_size = 100
        
        # Process symbols in batches
        for batch_start in range(0, len(symbols), batch_size):
            batch_end = min(batch_start + batch_size, len(symbols))
            batch_symbols = symbols[batch_start:batch_end]
            
            print(f"INFO: Processing batch {batch_start//batch_size + 1} ({batch_start + 1}-{batch_end} of {len(symbols)})")
            
            # Collect batch data
            batch_data = []
            
            for symbol in batch_symbols:
                try:
                    if symbol == 'SPY':
                        sector = 'ETF'
                        sic_description = 'Investment Fund'
                        sic_code = None
                    else:
                        details = client.client.get_ticker_details(symbol)
                        
                        sic_description = getattr(details, 'sic_description', None) or ''
                        sic_code = getattr(details, 'sic_code', None)
                        
                        if sic_description or sic_code:
                            sector = client._map_sic_to_sector(sic_description, str(sic_code) if sic_code else None)
                        elif hasattr(details, 'sector') and details.sector:
                            sector = details.sector
                        else:
                            sector = 'Unknown'
                    
                    batch_data.append({
                        "symbol": symbol,
                        "sector": sector,
                        "sic_description": sic_description,
                        "sic_code": sic_code
                    })
                    
                    successful_updates += 1
                    
                except Exception as e:
                    print(f"ERROR: Failed to process {symbol}: {e}")
                    batch_data.append({
                        "symbol": symbol,
                        "sector": 'Unknown',
                        "sic_description": '',
                        "sic_code": None
                    })
                    failed_updates += 1
            
            if batch_data:
                try:
                    with eng.begin() as conn:
                        for data in batch_data:
                            # Escape single quotes in text fields
                            symbol = data["symbol"].replace("'", "''")
                            sector = data["sector"].replace("'", "''")
                            sic_description = data["sic_description"].replace("'", "''")
                            sic_code = data["sic_code"] if data["sic_code"] is not None else "NULL"
                            
                            conn.execute(text(f"""
                                INSERT INTO sector_cache (symbol, sector, sic_description, sic_code, last_updated)
                                VALUES ('{symbol}', '{sector}', '{sic_description}', {sic_code}, CURRENT_DATE)
                                ON CONFLICT (symbol) DO UPDATE SET
                                    sector = '{sector}',
                                    sic_description = '{sic_description}',
                                    sic_code = {sic_code},
                                    last_updated = CURRENT_DATE
                            """))
                    
                    print(f"INFO: Saved batch of {len(batch_data)} records to database")
                    
                except Exception as e:
                    print(f"ERROR: Failed to save batch to database: {e}")

        return True
        
    except Exception as e:
        print(f"ERROR: Failed to update sector cache: {e}")
        return False

def verify_database_state():
    try:
        eng = get_engine()
        with eng.begin() as conn:
            sic_count = conn.execute(text("SELECT COUNT(*) FROM sic_codes")).scalar()
            print(f"SIC Codes: {sic_count} entries")
            
            symbols_count = conn.execute(text("SELECT COUNT(*) FROM symbols WHERE is_active = true")).scalar()
            print(f"Active Symbols: {symbols_count} entries")
            
            sector_count = conn.execute(text("SELECT COUNT(*) FROM sector_cache")).scalar()
            sector_unknown = conn.execute(text("SELECT COUNT(*) FROM sector_cache WHERE sector = 'Unknown'")).scalar()
            coverage_pct = ((sector_count - sector_unknown) / sector_count * 100) if sector_count > 0 else 0
            print(f"Sector Cache: {sector_count} entries ({coverage_pct:.1f}% classified)")
            
            sector_breakdown = conn.execute(text("""
                SELECT sector, COUNT(*) as count 
                FROM sector_cache 
                GROUP BY sector 
                ORDER BY count DESC
                LIMIT 5
            """)).fetchall()
        
            spy_count = conn.execute(text("SELECT COUNT(*) FROM symbols WHERE symbol = 'SPY'")).scalar()
            if spy_count > 0:
                print(f"SPY symbol present")
            else:
                print(f"SPY symbol missing")
            
        print("SUCCESS: Database verification completed")
        return True
        
    except Exception as e:
        print(f"ERROR: Database verification failed: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(
        description="Unified database maintenance for RapidTrader",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/update_database.py --all          # Full rebuild (recommended)
  python scripts/update_database.py --quick        # Quick update (skip SIC rebuild)
  python scripts/update_database.py --symbols      # Update symbols only
  python scripts/update_database.py --sectors      # Update sectors only
  python scripts/update_database.py --sic          # Update SIC codes only
  python scripts/update_database.py --cleanup      # Clean up orphaned sector_cache entries
        """
    )
    
    parser.add_argument("--all", action="store_true",
                       help="Perform complete database update (SIC + symbols + sectors)")
    parser.add_argument("--quick", action="store_true",
                       help="Quick update (symbols + sectors, skip SIC rebuild)")
    parser.add_argument("--sic", action="store_true",
                       help="Update SIC codes database only")
    parser.add_argument("--symbols", action="store_true",
                       help="Update symbols table only")
    parser.add_argument("--sectors", action="store_true",
                       help="Update sector cache only")
    parser.add_argument("--cleanup", action="store_true",
                       help="Clean up orphaned symbols from sector_cache")
    parser.add_argument("--clear", action="store_true",
                       help="Clear existing data before updating")
    
    args = parser.parse_args()
    
    api_key = settings.RT_POLYGON_API_KEY
    if not api_key:
        print("ERROR: Polygon API key required!")
        print("Set RT_POLYGON_API_KEY in your .env file")
        print("Get Polygon key at: https://polygon.io/")
        return 1
    
    update_sic = args.all or args.sic
    update_syms = args.all or args.quick or args.symbols
    update_secs = args.all or args.quick or args.sectors
    cleanup_cache = args.cleanup
    
    if not any([update_sic, update_syms, update_secs, cleanup_cache]):
        print("ERROR: No update operations specified!")
        print("Use --all, --quick, --cleanup, or specify individual components (--sic, --symbols, --sectors)")
        return 1
    
    success_count = 0
    total_operations = sum([update_sic, update_syms, update_secs, cleanup_cache])
    
    try:
        if update_sic:
            if update_sic_database():
                success_count += 1
            else:
                print("WARNING: Continuing with other operations despite SIC database failure")
        
        if update_syms:
            if update_symbols_table(clear_existing=args.clear):
                success_count += 1
            else:
                print("ERROR: Symbols update failed - aborting remaining operations")
                return 1
        
        if update_secs:
            if update_sector_cache(clear_existing=args.clear):
                success_count += 1
            else:
                print("ERROR: Sector cache update failed")
                return 1
        
        if cleanup_cache:
            if cleanup_sector_cache():
                success_count += 1
            else:
                print("ERROR: Sector cache cleanup failed")
                return 1

        verify_database_state()
        
        return 0
        
    except Exception as e:
        print(f"\nERROR: Database update failed: {e}")
        return 1

if __name__ == "__main__":
    exit(main())
