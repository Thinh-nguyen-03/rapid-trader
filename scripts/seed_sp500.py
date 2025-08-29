#!/usr/bin/env python3
"""
Seed the symbols table with S&P 500 stocks using Financial Modeling Prep (FMP) API.
Clean, simple implementation focused on reliable data.
"""

import sys
import os
import argparse
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from rapidtrader.core.db import get_engine
from rapidtrader.core.config import settings
from rapidtrader.data.sp500_api import get_sp500_symbols, map_sector_name
from sqlalchemy import text

def seed_symbols(source: str = "polygon", clear_existing: bool = False):
    """
    Fetch S&P 500 symbols and populate the database.
    
    Args:
        source: Data source ("polygon", "wikipedia", or "fmp")
        clear_existing: Whether to clear existing symbols first
    """
    print(f"Starting S&P 500 symbol seeding from {source.title()}...")
    
    try:
        # Fetch symbols from specified source
        symbols = get_sp500_symbols(source=source)
        print(f"Retrieved {len(symbols)} symbols from {source.title()}")
        
        # Connect to database
        eng = get_engine()
        
        with eng.begin() as c:
            if clear_existing:
                print("Clearing existing symbols...")
                c.execute(text("DELETE FROM symbols"))
            
            # Insert symbols
            print(f"Inserting {len(symbols)} symbols into database...")
            
            for symbol, sector in symbols:
                # Standardize sector name
                clean_sector = map_sector_name(sector)
                
                c.execute(text("""
                    INSERT INTO symbols (symbol, sector, is_active) 
                    VALUES (:symbol, :sector, true)
                    ON CONFLICT (symbol) DO UPDATE SET 
                        sector = :sector, 
                        is_active = true
                """), {"symbol": symbol, "sector": clean_sector})
            
            # Verify insertion
            count = c.execute(text("SELECT COUNT(*) FROM symbols WHERE is_active = true")).scalar()
            print(f"Successfully seeded {count} active symbols")
            
            # Show sector breakdown
            sectors = c.execute(text("""
                SELECT sector, COUNT(*) as count 
                FROM symbols 
                WHERE is_active = true 
                GROUP BY sector 
                ORDER BY count DESC
            """)).all()
            
            print("\nSector breakdown:")
            for sector, count in sectors:
                print(f"  {sector}: {count} symbols")
                
    except Exception as e:
        print(f"Error during symbol seeding: {e}")
        raise

def verify_symbols():
    """Verify the symbols table is properly populated."""
    print("\nVerifying symbol data...")
    
    try:
        eng = get_engine()
        
        with eng.begin() as c:
            # Total counts
            total = c.execute(text("SELECT COUNT(*) FROM symbols")).scalar()
            active = c.execute(text("SELECT COUNT(*) FROM symbols WHERE is_active = true")).scalar()
            
            print(f"Total symbols: {total}")
            print(f"Active symbols: {active}")
            
            # Sample symbols
            samples = c.execute(text("""
                SELECT symbol, sector 
                FROM symbols 
                WHERE is_active = true 
                ORDER BY symbol 
                LIMIT 10
            """)).all()
            
            print(f"\nSample symbols:")
            for symbol, sector in samples:
                print(f"  {symbol} ({sector})")
                
            # Check for required symbols
            spy_count = c.execute(text(
                "SELECT COUNT(*) FROM symbols WHERE symbol = 'SPY'"
            )).scalar()
            
            if spy_count == 0:
                print("⚠️  Warning: SPY not found - market filter may not work")
            else:
                print("✓ SPY found - market filter ready")
                
    except Exception as e:
        print(f"Error during verification: {e}")
        raise

def main():
    """Main entry point with command line argument parsing."""
    parser = argparse.ArgumentParser(description="Seed S&P 500 symbols from Wikipedia or FMP API")
    parser.add_argument("--source", choices=["polygon", "wikipedia", "fmp"], default="polygon",
                       help="Data source for S&P 500 symbols (default: polygon)")
    parser.add_argument("--clear", action="store_true", 
                       help="Clear existing symbols before seeding")
    
    args = parser.parse_args()
    
    # Check if API keys are needed
    if args.source == "polygon":
        api_key = settings.RT_POLYGON_API_KEY
        if not api_key:
            print("❌ Polygon API key required for Polygon source!")
            print("Either:")
            print("  1. Set RT_POLYGON_API_KEY in your .env file")
            print("  2. Use --source wikipedia (no API key needed)")
            print("  3. Get Polygon key at: https://polygon.io/")
            sys.exit(1)
    elif args.source == "fmp":
        api_key = getattr(settings, 'RT_FMP_API_KEY', None)
        if not api_key:
            print("❌ FMP API key required for FMP source!")
            print("Either:")
            print("  1. Set RT_FMP_API_KEY in your .env file")
            print("  2. Use --source wikipedia (no API key needed)")
            print("  3. Get FMP key at: https://financialmodelingprep.com/developer/docs")
            sys.exit(1)
    
    try:
        # Run seeding
        seed_symbols(source=args.source, clear_existing=args.clear)
        verify_symbols()
        
        print("\n✅ S&P 500 symbol seeding completed successfully!")
        print("\nNext steps:")
        print("  1. Test data ingestion with a few symbols")
        print("  2. Run full data pipeline")
        
    except Exception as e:
        print(f"\n❌ Symbol seeding failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()