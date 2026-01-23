#!/usr/bin/env python3
"""Quick test script to verify Alpaca migration is working."""

import sys
from datetime import date, timedelta
from rapidtrader.core.config import settings
from rapidtrader.data.ingest import AlpacaDataClient

def test_alpaca_connection():
    """Test basic Alpaca data connection and fetch."""
    print("=" * 60)
    print("Testing Alpaca Data Migration")
    print("=" * 60)

    # Check credentials
    print("\n1. Checking Alpaca credentials...")
    if not settings.RT_ALPACA_API_KEY:
        print("❌ ERROR: RT_ALPACA_API_KEY not set in .env")
        return False
    if not settings.RT_ALPACA_SECRET_KEY:
        print("❌ ERROR: RT_ALPACA_SECRET_KEY not set in .env")
        return False
    print("✅ Alpaca credentials found")

    # Test data fetch
    print("\n2. Testing data fetch for SPY...")
    try:
        client = AlpacaDataClient(
            api_key=settings.RT_ALPACA_API_KEY,
            secret_key=settings.RT_ALPACA_SECRET_KEY
        )

        end_date = date.today()
        start_date = end_date - timedelta(days=30)

        df = client.get_daily_bars('SPY', start_date, end_date)

        if df.empty:
            print("❌ ERROR: No data returned")
            return False

        print(f"✅ Successfully fetched {len(df)} bars for SPY")
        print(f"\nSample data:")
        print(df.tail(3))

        # Test previous close
        print("\n3. Testing previous close fetch...")
        prev_close = client.get_previous_close('SPY')
        if prev_close:
            print(f"✅ Latest close for SPY: ${prev_close['close']:.2f}")
        else:
            print("⚠️  WARNING: Could not fetch previous close")

        print("\n" + "=" * 60)
        print("✅ All tests passed! Alpaca migration successful!")
        print("=" * 60)
        return True

    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_alpaca_connection()
    sys.exit(0 if success else 1)
