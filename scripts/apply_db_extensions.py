#!/usr/bin/env python3
"""Apply database extensions for RapidTrader reliability features.

This script adds the system_state and exec_fills tables needed for
kill switch functionality and broker reconciliation.
"""

import sys
from pathlib import Path
from sqlalchemy import text

# Add parent directory to path so we can import rapidtrader
sys.path.append(str(Path(__file__).parent.parent))

from rapidtrader.core.db import get_engine


def apply_extensions():
    """Apply database extensions from SQL file."""
    
    # Read the SQL file
    sql_file = Path(__file__).parent / "setup_db_extensions.sql"
    
    if not sql_file.exists():
        print(f"ERROR: SQL file not found: {sql_file}")
        return False
    
    sql_content = sql_file.read_text()
    
    # Apply to database
    try:
        eng = get_engine()
        
        print("Applying database extensions...")
        
        # Execute the entire SQL content as one transaction
        with eng.begin() as conn:
            print("  Executing SQL statements...")
            # Remove comments that start with -- to avoid issues
            cleaned_sql = '\n'.join([
                line for line in sql_content.split('\n') 
                if not line.strip().startswith('--')
            ])
            conn.execute(text(cleaned_sql))
        
        print("SUCCESS: Database extensions applied successfully!")
        return True
        
    except Exception as e:
        print(f"ERROR: Failed to apply database extensions: {e}")
        return False


def verify_extensions():
    """Verify that the extensions were applied correctly."""
    
    try:
        eng = get_engine()
        
        print("\nVerifying extensions...")
        
        # Check system_state table
        with eng.begin() as conn:
            result = conn.execute(text("""
                SELECT COUNT(*) FROM information_schema.tables 
                WHERE table_name = 'system_state'
            """)).scalar_one()
            
            if result > 0:
                print("  SUCCESS: system_state table exists")
            else:
                print("  ERROR: system_state table missing")
                return False
        
        # Check exec_fills table
        with eng.begin() as conn:
            result = conn.execute(text("""
                SELECT COUNT(*) FROM information_schema.tables 
                WHERE table_name = 'exec_fills'
            """)).scalar_one()
            
            if result > 0:
                print("  SUCCESS: exec_fills table exists")
            else:
                print("  ERROR: exec_fills table missing")
                return False
        
        print("SUCCESS: All extensions verified!")
        return True
        
    except Exception as e:
        print(f"ERROR: Failed to verify extensions: {e}")
        return False


if __name__ == "__main__":
    print("RapidTrader Database Extensions Setup")
    print("=" * 45)
    
    # Apply extensions
    if not apply_extensions():
        exit(1)
    
    # Verify
    if not verify_extensions():
        exit(1)
    
    print("\nSUCCESS: Setup complete! Kill switch functionality is now available.")
    print("\nNext steps:")
    print("  1. Test with: python -m rapidtrader.jobs.paper_daily --dry-run")
    print("  2. Check kill switch: python -m rapidtrader.risk.kill_switch --check")
