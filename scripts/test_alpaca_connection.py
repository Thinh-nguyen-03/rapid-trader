#!/usr/bin/env python3
"""Test Alpaca API Connection for RapidTrader.

This script tests your Alpaca API credentials and paper trading setup
to ensure everything is working before integrating with the trading system.
"""

import sys
from pathlib import Path

# Add parent directory to path so we can import rapidtrader
sys.path.append(str(Path(__file__).parent.parent))

from rapidtrader.core.config import settings

try:
    from alpaca.trading.client import TradingClient
    from alpaca.trading.requests import GetAssetsRequest
    from alpaca.trading.enums import AssetClass
except ImportError:
    print("ERROR: Alpaca SDK not installed. Run: pip install alpaca-py")
    exit(1)


def test_connection():
    """Test basic connection to Alpaca API."""
    try:
        # Initialize client
        client = TradingClient(
            api_key=settings.RT_ALPACA_API_KEY,
            secret_key=settings.RT_ALPACA_SECRET_KEY,
            paper=settings.RT_ALPACA_PAPER
        )
        
        print("Testing connection to Alpaca API...")
        
        # Test account access
        account = client.get_account()
        print(f"SUCCESS: Account connected: {account.id}")
        print(f"   Account Status: {account.status}")
        print(f"   Buying Power: ${float(account.buying_power):,.2f}")
        print(f"   Portfolio Value: ${float(account.portfolio_value):,.2f}")
        print(f"   Paper Trading: {settings.RT_ALPACA_PAPER}")
        
        return True
        
    except Exception as e:
        print(f"ERROR: Connection failed: {e}")
        return False


def test_asset_lookup():
    """Test looking up tradeable assets."""
    try:
        client = TradingClient(
            api_key=settings.RT_ALPACA_API_KEY,
            secret_key=settings.RT_ALPACA_SECRET_KEY,
            paper=settings.RT_ALPACA_PAPER
        )
        
        print("\nTesting asset lookup...")
        
        # Get some sample assets
        search_params = GetAssetsRequest(
            asset_class=AssetClass.US_EQUITY
        )
        
        assets = client.get_all_assets(search_params)
        
        # Filter for some S&P 500 symbols we use
        test_symbols = ['AAPL', 'MSFT', 'GOOGL', 'TSLA', 'SPY']
        found_symbols = []
        
        for asset in assets:
            if asset.symbol in test_symbols and asset.tradable:
                found_symbols.append(asset.symbol)
                print(f"   SUCCESS: {asset.symbol}: {asset.name} (tradable: {asset.tradable})")
                
        if len(found_symbols) >= 3:
            print(f"SUCCESS: Asset lookup successful: {len(found_symbols)} test symbols found")
            return True
        else:
            print(f"WARNING: Only found {len(found_symbols)} tradable symbols")
            return False
            
    except Exception as e:
        print(f"ERROR: Asset lookup failed: {e}")
        return False


def test_market_hours():
    """Test market hours and trading calendar."""
    try:
        client = TradingClient(
            api_key=settings.RT_ALPACA_API_KEY,
            secret_key=settings.RT_ALPACA_SECRET_KEY,
            paper=settings.RT_ALPACA_PAPER
        )
        
        print("\nTesting market hours...")
        
        # Get clock info
        clock = client.get_clock()
        print(f"   Market Open: {clock.is_open}")
        print(f"   Next Open: {clock.next_open}")
        print(f"   Next Close: {clock.next_close}")
        print(f"   Timezone: {clock.timestamp.tzinfo}")
        
        print("SUCCESS: Market hours lookup successful")
        return True
        
    except Exception as e:
        print(f"ERROR: Market hours lookup failed: {e}")
        return False


def test_positions():
    """Test positions lookup (should be empty for new paper account)."""
    try:
        client = TradingClient(
            api_key=settings.RT_ALPACA_API_KEY,
            secret_key=settings.RT_ALPACA_SECRET_KEY,
            paper=settings.RT_ALPACA_PAPER
        )
        
        print("\nTesting positions lookup...")
        
        positions = client.get_all_positions()
        print(f"   Current Positions: {len(positions)}")
        
        if positions:
            for pos in positions[:5]:  # Show first 5
                print(f"   - {pos.symbol}: {pos.qty} shares @ ${float(pos.avg_entry_price):.2f}")
        else:
            print("   INFO: No current positions (clean paper account)")
        
        print("SUCCESS: Positions lookup successful")
        return True
        
    except Exception as e:
        print(f"ERROR: Positions lookup failed: {e}")
        return False


def show_configuration():
    """Show current configuration."""
    print("\nCurrent Configuration:")
    print(f"   API Key: {settings.RT_ALPACA_API_KEY[:8]}...")
    print(f"   Paper Trading: {settings.RT_ALPACA_PAPER}")
    print(f"   Endpoint: {settings.RT_ALPACA_ENDPOINT}")
    
    if not settings.RT_ALPACA_PAPER:
        print("   WARNING: Live trading mode detected!")
        print("   INFO: Set RT_ALPACA_PAPER=true for safe paper trading")


def main():
    """Run all connection tests."""
    print("RapidTrader Alpaca Connection Test")
    print("=" * 40)
    
    # Show configuration
    show_configuration()
    
    # Run tests
    tests = [
        ("Connection", test_connection),
        ("Asset Lookup", test_asset_lookup),
        ("Market Hours", test_market_hours),
        ("Positions", test_positions),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        print(f"\nRunning {test_name} Test...")
        results[test_name] = test_func()
    
    # Summary
    print("\n" + "=" * 40)
    print("Test Results Summary:")
    
    passed = 0
    for test_name, result in results.items():
        status = "PASS" if result else "FAIL"
        print(f"   {test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{len(tests)} tests passed")
    
    if passed == len(tests):
        print("\nSUCCESS: All tests passed! Alpaca integration is ready.")
        print("\nNext Steps:")
        print("   1. Your paper trading account is connected")
        print("   2. Ready to integrate with RapidTrader daily workflow")
        print("   3. Orders will be placed automatically via Alpaca Paper API")
        return 0
    else:
        print("\nERROR: Some tests failed. Please check your configuration.")
        return 1


if __name__ == "__main__":
    exit(main())
