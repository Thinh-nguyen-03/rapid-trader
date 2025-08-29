#!/usr/bin/env python3
"""
Test Polygon.io API integration for S&P 500 data fetching and OHLCV ingestion.
Simple test to verify the API key and data retrieval work correctly.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from rapidtrader.data.sp500_api import PolygonClient, get_sp500_symbols
from rapidtrader.data.ingest import PolygonDataClient, ingest_symbol
from rapidtrader.core.config import settings
from datetime import date, timedelta
import pandas as pd


def test_polygon_connection():
    """Test basic Polygon.io API connectivity."""
    print("Testing Polygon.io API connection...")
    
    api_key = settings.RT_POLYGON_API_KEY or input("Enter your Polygon API key: ").strip()
    
    if not api_key:
        print("❌ No API key provided")
        return False
    
    try:
        client = PolygonClient(api_key)
        
        # Test basic ticker listing
        print("Testing ticker listing...")
        tickers = []
        count = 0
        for ticker in client.client.list_tickers(market="stocks", active=True, limit=10):
            tickers.append(ticker)
            count += 1
            if count >= 10:  # Just test first 10
                break
        
        if not tickers:
            print("❌ No ticker data received from Polygon.io")
            return False
        
        print(f"✅ Successfully retrieved {len(tickers)} sample tickers")
        
        # Show sample data
        print(f"\nSample tickers:")
        for ticker in tickers[:5]:
            print(f"  {ticker.ticker} - {getattr(ticker, 'name', 'N/A')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Polygon.io API test failed: {e}")
        return False


def test_ohlcv_data():
    """Test OHLCV data retrieval."""
    print("\nTesting OHLCV data retrieval...")
    
    api_key = settings.RT_POLYGON_API_KEY
    if not api_key:
        print("❌ No API key configured")
        return False
    
    try:
        client = PolygonDataClient(api_key)
        
        # Test with SPY (should have good data)
        symbol = "SPY"
        end_date = date.today()
        start_date = end_date - timedelta(days=30)
        
        print(f"Fetching {symbol} data for last 30 days...")
        df = client.get_daily_bars(symbol, start_date, end_date)
        
        if df.empty:
            print(f"❌ No OHLCV data received for {symbol}")
            return False
        
        print(f"✅ Successfully retrieved {len(df)} days of {symbol} data")
        
        # Show sample data
        print(f"\nSample {symbol} data (last 5 days):")
        print(df.tail().to_string())
        
        # Test previous close
        print(f"\nTesting previous close for {symbol}...")
        prev_close = client.get_previous_close(symbol)
        
        if prev_close:
            print(f"✅ Previous close: ${prev_close['close']:.2f}")
        else:
            print("⚠️  No previous close data available")
        
        return True
        
    except Exception as e:
        print(f"❌ OHLCV data test failed: {e}")
        return False


def test_s500_symbol_fetching():
    """Test S&P 500 symbol processing."""
    print("\nTesting S&P 500 symbol fetching...")
    
    try:
        # Test with Polygon source
        print("Testing Polygon.io S&P 500 symbol fetching...")
        symbols = get_sp500_symbols(source="polygon")
        
        if not symbols:
            print("❌ No symbols returned from Polygon")
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
        
        print(f"\nSector distribution (top 5):")
        for sector, count in sorted(sectors.items(), key=lambda x: x[1], reverse=True)[:5]:
            print(f"  {sector}: {count} symbols")
        
        # Show sample symbols
        print(f"\nSample symbols:")
        for symbol, sector in symbols[:10]:
            print(f"  {symbol} ({sector})")
        
        return True
        
    except Exception as e:
        print(f"❌ S&P 500 symbol test failed: {e}")
        return False


def test_data_ingestion():
    """Test data ingestion for a single symbol."""
    print("\nTesting data ingestion...")
    
    try:
        # Test ingesting a single symbol
        symbol = "AAPL"
        print(f"Testing data ingestion for {symbol}...")
        
        # This would normally store to database, but we'll just test the API call
        api_key = settings.RT_POLYGON_API_KEY
        if not api_key:
            print("❌ No API key configured")
            return False
        
        client = PolygonDataClient(api_key)
        
        # Fetch 30 days of data
        end_date = date.today()
        start_date = end_date - timedelta(days=30)
        
        df = client.get_daily_bars(symbol, start_date, end_date)
        
        if df.empty:
            print(f"❌ No data retrieved for {symbol}")
            return False
        
        print(f"✅ Successfully fetched {len(df)} days of {symbol} data")
        
        # Validate data structure
        expected_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
        if not all(col in df.columns for col in expected_columns):
            print(f"❌ Missing expected columns. Got: {list(df.columns)}")
            return False
        
        # Check for reasonable data
        if df['Close'].iloc[-1] <= 0:
            print(f"❌ Invalid closing price: {df['Close'].iloc[-1]}")
            return False
        
        print(f"✅ Data validation passed. Latest close: ${df['Close'].iloc[-1]:.2f}")
        
        return True
        
    except Exception as e:
        print(f"❌ Data ingestion test failed: {e}")
        return False


def main():
    """Run all Polygon.io tests."""
    print("=" * 60)
    print("Polygon.io API Integration Test")
    print("=" * 60)
    
    # Check API key
    api_key = settings.RT_POLYGON_API_KEY
    if not api_key:
        print("⚠️  No Polygon API key found in config")
        print("Get your free key at: https://polygon.io/")
        print("Then set RT_POLYGON_API_KEY in your .env file")
        print()
    
    # Run tests
    tests = [
        test_polygon_connection,
        test_ohlcv_data,
        test_s500_symbol_fetching,
        test_data_ingestion
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
    
    print("=" * 60)
    print(f"Test Results: {passed}/{total} passed")
    
    if passed == total:
        print("🎉 All tests passed! Polygon.io integration is working correctly.")
        print("\nNext steps:")
        print("  1. Run: python scripts/seed_sp500.py --source polygon")
        print("  2. Test data ingestion with a few symbols")
        print("  3. Run full data pipeline")
        return 0
    else:
        print("❌ Some tests failed. Check your Polygon API key and connection.")
        print("\nTroubleshooting:")
        print("  1. Verify your API key is correct")
        print("  2. Check you haven't exceeded rate limits")
        print("  3. Ensure you have an active Polygon.io account")
        return 1


if __name__ == "__main__":
    sys.exit(main())
