#!/usr/bin/env python3
"""
Standalone script to clean up orphaned symbols from sector_cache table.
This removes symbols that are not in the active symbols table.
"""

import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rapidtrader.core.db import get_engine
from sqlalchemy import text

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
            
            # Show final counts
            symbols_count = conn.execute(text("SELECT COUNT(*) FROM symbols WHERE is_active = true")).scalar()
            sector_count = conn.execute(text("SELECT COUNT(*) FROM sector_cache")).scalar()
            
            print(f"INFO: Active symbols: {symbols_count}")
            print(f"INFO: Sector cache entries: {sector_count}")
            
            return True
            
    except Exception as e:
        print(f"ERROR: Failed to cleanup sector_cache: {e}")
        return False

def main():
    print("INFO: Starting sector_cache cleanup...")
    
    if cleanup_sector_cache():
        print("SUCCESS: Sector cache cleanup completed")
        return 0
    else:
        print("ERROR: Sector cache cleanup failed")
        return 1

if __name__ == "__main__":
    exit(main())
