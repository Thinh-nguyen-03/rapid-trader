#!/usr/bin/env python3
"""
Test script to validate local indicator calculations against real market data.
Compares our SMA, RSI, and ATR implementations with known correct values.
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import date, timedelta

# Add the project root to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from rapidtrader.core.config import settings
from rapidtrader.data.ingest import PolygonDataClient
from rapidtrader.indicators.core import sma, rsi_wilder, atr


def get_test_data(symbol: str = "AAPL", days: int = 100) -> pd.DataFrame:
    """Fetch real market data for testing."""
    print(f"Fetching {days} days of {symbol} data from Polygon...")
    
    api_key = settings.RT_POLYGON_API_KEY
    if not api_key:
        raise ValueError("Polygon API key not found. Set RT_POLYGON_API_KEY in .env file")
    
    client = PolygonDataClient(api_key)
    
    end_date = date.today()
    start_date = end_date - timedelta(days=days)
    
    df = client.get_daily_bars(symbol, start_date, end_date)
    
    if df.empty:
        raise ValueError(f"No data retrieved for {symbol}")
    
    print(f"✅ Retrieved {len(df)} bars for {symbol}")
    print(f"Date range: {df.index.min()} to {df.index.max()}")
    print(f"Price range: ${df['Close'].min():.2f} - ${df['Close'].max():.2f}")
    
    return df


def test_sma_calculation(df: pd.DataFrame, periods: list = [10, 20, 50]) -> bool:
    """Test Simple Moving Average calculations."""
    print("\n" + "="*60)
    print("🔍 TESTING SIMPLE MOVING AVERAGE (SMA)")
    print("="*60)
    
    all_passed = True
    
    for period in periods:
        print(f"\nTesting SMA({period})...")
        
        # Calculate using our function
        our_sma = sma(df['Close'], period)
        
        # Calculate using pandas for comparison
        pandas_sma = df['Close'].rolling(window=period, min_periods=period).mean()
        
        # Compare non-NaN values
        valid_mask = ~(our_sma.isna() | pandas_sma.isna())
        our_valid = our_sma[valid_mask]
        pandas_valid = pandas_sma[valid_mask]
        
        if len(our_valid) == 0:
            print(f"  ⚠️  No valid data for SMA({period}) - insufficient history")
            continue
        
        # Calculate differences
        diff = np.abs(our_valid - pandas_valid)
        max_diff = diff.max()
        mean_diff = diff.mean()
        
        # Tolerance for floating point precision
        tolerance = 1e-10
        
        if max_diff < tolerance:
            print(f"  ✅ SMA({period}): PASSED")
            print(f"     Values count: {len(our_valid)}")
            print(f"     Max difference: {max_diff:.2e}")
            print(f"     Sample values: {our_valid.tail(3).round(2).tolist()}")
        else:
            print(f"  ❌ SMA({period}): FAILED")
            print(f"     Max difference: {max_diff:.6f} (tolerance: {tolerance})")
            print(f"     Mean difference: {mean_diff:.6f}")
            all_passed = False
    
    return all_passed


def test_rsi_calculation(df: pd.DataFrame, periods: list = [14, 21]) -> bool:
    """Test RSI (Wilder's method) calculations."""
    print("\n" + "="*60)
    print("🔍 TESTING RELATIVE STRENGTH INDEX (RSI)")
    print("="*60)
    
    all_passed = True
    
    for period in periods:
        print(f"\nTesting RSI({period}) using Wilder's smoothing...")
        
        # Calculate using our function
        our_rsi = rsi_wilder(df['Close'], period)
        
        # Manual calculation for verification
        def manual_rsi_wilder(close_prices, window):
            """Manual RSI calculation using Wilder's method for verification."""
            delta = close_prices.diff()
            gain = delta.clip(lower=0.0)
            loss = -delta.clip(upper=0.0)
            
            # Wilder's smoothing (exponential with alpha=1/period)
            avg_gain = gain.ewm(alpha=1/window, adjust=False).mean()
            avg_loss = loss.ewm(alpha=1/window, adjust=False).mean()
            
            rs = avg_gain / avg_loss.replace(0, np.nan)
            rsi = 100 - (100 / (1 + rs))
            return rsi
        
        manual_rsi = manual_rsi_wilder(df['Close'], period)
        
        # Compare non-NaN values
        valid_mask = ~(our_rsi.isna() | manual_rsi.isna())
        our_valid = our_rsi[valid_mask]
        manual_valid = manual_rsi[valid_mask]
        
        if len(our_valid) == 0:
            print(f"  ⚠️  No valid data for RSI({period}) - insufficient history")
            continue
        
        # Calculate differences
        diff = np.abs(our_valid - manual_valid)
        max_diff = diff.max()
        mean_diff = diff.mean()
        
        # RSI tolerance (slightly higher due to cumulative calculations)
        tolerance = 1e-8
        
        if max_diff < tolerance:
            print(f"  ✅ RSI({period}): PASSED")
            print(f"     Values count: {len(our_valid)}")
            print(f"     Max difference: {max_diff:.2e}")
            print(f"     Value range: {our_valid.min():.1f} - {our_valid.max():.1f}")
            print(f"     Sample values: {our_valid.tail(3).round(1).tolist()}")
            
            # Check for reasonable RSI values (0-100)
            if our_valid.min() >= 0 and our_valid.max() <= 100:
                print(f"     ✅ Values within valid RSI range (0-100)")
            else:
                print(f"     ❌ Values outside valid RSI range!")
                all_passed = False
                
        else:
            print(f"  ❌ RSI({period}): FAILED")
            print(f"     Max difference: {max_diff:.6f} (tolerance: {tolerance})")
            print(f"     Mean difference: {mean_diff:.6f}")
            all_passed = False
    
    return all_passed


def test_atr_calculation(df: pd.DataFrame, periods: list = [14, 20]) -> bool:
    """Test Average True Range calculations."""
    print("\n" + "="*60)
    print("🔍 TESTING AVERAGE TRUE RANGE (ATR)")
    print("="*60)
    
    all_passed = True
    
    for period in periods:
        print(f"\nTesting ATR({period})...")
        
        # Calculate using our function
        our_atr = atr(df['High'], df['Low'], df['Close'], period)
        
        # Manual calculation for verification
        def manual_atr(high, low, close, window):
            """Manual ATR calculation for verification."""
            prev_close = close.shift(1)
            tr1 = high - low
            tr2 = (high - prev_close).abs()
            tr3 = (low - prev_close).abs()
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            
            # Wilder's smoothing
            atr_manual = tr.ewm(alpha=1/window, adjust=False, min_periods=window).mean()
            return atr_manual
        
        manual_atr = manual_atr(df['High'], df['Low'], df['Close'], period)
        
        # Compare non-NaN values
        valid_mask = ~(our_atr.isna() | manual_atr.isna())
        our_valid = our_atr[valid_mask]
        manual_valid = manual_atr[valid_mask]
        
        if len(our_valid) == 0:
            print(f"  ⚠️  No valid data for ATR({period}) - insufficient history")
            continue
        
        # Calculate differences
        diff = np.abs(our_valid - manual_valid)
        max_diff = diff.max()
        mean_diff = diff.mean()
        
        # ATR tolerance (considering price magnitude)
        tolerance = 1e-8
        
        if max_diff < tolerance:
            print(f"  ✅ ATR({period}): PASSED")
            print(f"     Values count: {len(our_valid)}")
            print(f"     Max difference: {max_diff:.2e}")
            print(f"     ATR range: ${our_valid.min():.2f} - ${our_valid.max():.2f}")
            print(f"     Sample values: ${our_valid.tail(3).round(2).tolist()}")
            
            # Check for reasonable ATR values (positive)
            if our_valid.min() > 0:
                print(f"     ✅ All ATR values are positive")
            else:
                print(f"     ❌ Some ATR values are non-positive!")
                all_passed = False
                
        else:
            print(f"  ❌ ATR({period}): FAILED")
            print(f"     Max difference: {max_diff:.6f} (tolerance: {tolerance})")
            print(f"     Mean difference: {mean_diff:.6f}")
            all_passed = False
    
    return all_passed


def test_edge_cases(df: pd.DataFrame) -> bool:
    """Test edge cases and error conditions."""
    print("\n" + "="*60)
    print("🔍 TESTING EDGE CASES")
    print("="*60)
    
    all_passed = True
    
    print("\nTesting insufficient data scenarios...")
    
    # Test with very short data
    short_data = df['Close'].head(5)
    
    try:
        # SMA with period longer than data
        result = sma(short_data, 10)
        if result.dropna().empty:
            print("  ✅ SMA handles insufficient data correctly (returns NaN)")
        else:
            print("  ❌ SMA should return NaN for insufficient data")
            all_passed = False
    except Exception as e:
        print(f"  ❌ SMA raised exception with insufficient data: {e}")
        all_passed = False
    
    try:
        # RSI with insufficient data
        result = rsi_wilder(short_data, 14)
        # RSI should have some NaN values at the beginning
        if result.isna().any():
            print("  ✅ RSI handles insufficient data correctly (some NaN values)")
        else:
            print("  ❌ RSI should have NaN values for initial periods")
            all_passed = False
    except Exception as e:
        print(f"  ❌ RSI raised exception with insufficient data: {e}")
        all_passed = False
    
    print("\nTesting boundary conditions...")
    
    # Test with constant prices (no volatility)
    constant_price = pd.Series([100.0] * 30, index=range(30))
    
    try:
        rsi_constant = rsi_wilder(constant_price, 14)
        # RSI should be around 50 for constant prices (no gains or losses)
        valid_rsi = rsi_constant.dropna()
        if not valid_rsi.empty:
            avg_rsi = valid_rsi.mean()
            if 45 <= avg_rsi <= 55:  # Allow some tolerance
                print(f"  ✅ RSI handles constant prices correctly (avg: {avg_rsi:.1f})")
            else:
                print(f"  ❌ RSI for constant prices should be ~50, got {avg_rsi:.1f}")
                all_passed = False
        else:
            print("  ⚠️  RSI returned no valid values for constant prices")
    except Exception as e:
        print(f"  ❌ RSI failed with constant prices: {e}")
        all_passed = False
    
    return all_passed


def generate_summary_report(test_results: dict, df: pd.DataFrame):
    """Generate a comprehensive test summary."""
    print("\n" + "="*80)
    print("📊 TEST SUMMARY REPORT")
    print("="*80)
    
    total_tests = len(test_results)
    passed_tests = sum(test_results.values())
    
    print(f"\nTest Results: {passed_tests}/{total_tests} passed")
    
    for test_name, passed in test_results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"  {test_name}: {status}")
    
    print(f"\nTest Data Statistics:")
    print(f"  Symbol: Market data from Polygon.io")
    print(f"  Bars count: {len(df)}")
    print(f"  Date range: {df.index.min()} to {df.index.max()}")
    print(f"  Price range: ${df['Close'].min():.2f} - ${df['Close'].max():.2f}")
    print(f"  Average volume: {df['Volume'].mean():,.0f}")
    
    print(f"\nIndicator Implementation Status:")
    if test_results.get('SMA Test', False):
        print(f"  ✅ SMA: Production ready")
    else:
        print(f"  ❌ SMA: Needs attention")
        
    if test_results.get('RSI Test', False):
        print(f"  ✅ RSI: Production ready")
    else:
        print(f"  ❌ RSI: Needs attention")
        
    if test_results.get('ATR Test', False):
        print(f"  ✅ ATR: Production ready")
    else:
        print(f"  ❌ ATR: Needs attention")
    
    print(f"\n💡 Performance Notes:")
    print(f"  - All calculations use vectorized pandas operations")
    print(f"  - RSI uses Wilder's exponential smoothing method")
    print(f"  - ATR uses Wilder's smoothing for consistency")
    print(f"  - Calculations handle NaN values appropriately")
    
    if passed_tests == total_tests:
        print(f"\n🎉 ALL TESTS PASSED!")
        print(f"   Your indicator implementations are accurate and ready for production use.")
        print(f"   You can proceed with confidence to strategy implementation (Phase 3).")
    else:
        print(f"\n⚠️  SOME TESTS FAILED!")
        print(f"   Please review the failed tests above and fix the implementations.")
        print(f"   Do not proceed to strategy implementation until all tests pass.")


def main():
    """Main test execution."""
    print("🔬 Technical Indicator Accuracy Test")
    print("="*80)
    print("Testing local indicator calculations against real market data...")
    print("This validates our SMA, RSI, and ATR implementations.")
    
    try:
        # Get test data
        df = get_test_data("AAPL", 100)  # 100 days should be enough for all tests
        
        # Run all tests
        test_results = {}
        
        test_results['SMA Test'] = test_sma_calculation(df)
        test_results['RSI Test'] = test_rsi_calculation(df) 
        test_results['ATR Test'] = test_atr_calculation(df)
        test_results['Edge Cases'] = test_edge_cases(df)
        
        # Generate summary
        generate_summary_report(test_results, df)
        
        # Return appropriate exit code
        if all(test_results.values()):
            return 0
        else:
            return 1
            
    except Exception as e:
        print(f"\n❌ Test execution failed: {e}")
        print("Please check your API key and network connection.")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
