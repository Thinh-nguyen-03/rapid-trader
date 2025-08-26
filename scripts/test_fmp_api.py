#!/usr/bin/env python3
"""
Test FMP API integration for S&P 500 data fetching.
Simple test to verify the API key and data retrieval work correctly.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from rapidtrader.data.sp500_api import FMPClient, get_sp500_symbols
from rapidtrader.core.config import settings

def test_fmp_connection():
    """Test basic FMP API connectivity."""
    print("Testing FMP API connection...")
    
    api_key = settings.RT_FMP_API_KEY or input("Enter your FMP API key: ").strip()
    
    if not api_key:
        print("❌ No API key provided")
        return False
    
    try:
        client = FMPClient(api_key)
        df = client.get_sp500_constituents()
        
        if df.empty:
            print("❌ No data received from FMP")
            return False
        
        print(f"✅ Successfully retrieved {len(df)} S&P 500 constituents")
        
        # Show sample data
        print(f"\nSample data (first 5 rows):")
        print(df.head()[['symbol', 'name', 'sector']].to_string(index=False))
        
        return True
        
    except Exception as e:
        print(f"❌ FMP API test failed: {e}")
        return False

def test_symbol_processing():
    """Test symbol processing and standardization."""
    print("\nTesting symbol processing...")
    
    try:
        symbols = get_sp500_symbols()
        
        if not symbols:
            print("❌ No symbols returned")
            return False
        
        print(f"✅ Processed {len(symbols)} symbols successfully")
        
        # Check for required symbols
        spy_found = any(symbol == 'SPY' for symbol, _ in symbols)
        if spy_found:
            print("✅ SPY found (required for market filter)")
        else:
            print("⚠️  SPY not found - will be added automatically")
        
        # Show sector distribution
        sectors = {}
        for symbol, sector in symbols:
            sectors[sector] = sectors.get(sector, 0) + 1
        
        print(f"\nSector distribution:")
        for sector, count in sorted(sectors.items(), key=lambda x: x[1], reverse=True):
            print(f"  {sector}: {count} symbols")
        
        return True
        
    except Exception as e:
        print(f"❌ Symbol processing test failed: {e}")
        return False

def main():
    """Run all FMP tests."""
    print("=" * 50)
    print("FMP API Integration Test")
    print("=" * 50)
    
    # Check API key
    api_key = settings.RT_FMP_API_KEY
    if not api_key:
        print("⚠️  No FMP API key found in config")
        print("Get your free key at: https://financialmodelingprep.com/developer/docs")
        print("Then set RT_FMP_API_KEY in your .env file")
        print()
    
    # Run tests
    tests = [
        test_fmp_connection,
        test_symbol_processing
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
            results.append(False)
        print()
    
    # Summary
    passed = sum(results)
    total = len(results)
    
    print("=" * 50)
    print(f"Test Results: {passed}/{total} passed")
    
    if passed == total:
        print("🎉 All tests passed! FMP integration is working correctly.")
        print("\nNext step: Run python scripts/seed_sp500.py")
        return 0
    else:
        print("❌ Some tests failed. Check your FMP API key and connection.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
