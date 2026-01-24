"""Unit tests for technical indicators.

These tests verify correctness against known values and edge cases.
"""
import pytest
import pandas as pd
import numpy as np
from rapidtrader.indicators.core import sma, rsi_wilder, atr


class TestSMA:
    """Test Simple Moving Average calculations."""

    def test_sma_basic(self):
        """Test SMA with simple known values."""
        series = pd.Series([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
        result = sma(series, n=3)

        # First two values should be NaN (not enough data)
        assert pd.isna(result.iloc[0])
        assert pd.isna(result.iloc[1])

        # Third value should be mean of first 3 values
        assert result.iloc[2] == 2.0  # (1+2+3)/3
        assert result.iloc[3] == 3.0  # (2+3+4)/3
        assert result.iloc[9] == 9.0  # (8+9+10)/3

    def test_sma_with_nan_values(self):
        """Test SMA handles NaN values gracefully."""
        series = pd.Series([1.0, 2.0, np.nan, 4.0, 5.0])
        result = sma(series, n=2)

        # Should propagate NaN appropriately
        assert pd.notna(result.iloc[1])  # (1+2)/2 = 1.5
        assert pd.isna(result.iloc[2])   # Contains NaN

    def test_sma_empty_series(self):
        """Test SMA with empty input."""
        series = pd.Series([], dtype=float)
        result = sma(series, n=3)
        assert len(result) == 0

    def test_sma_window_larger_than_series(self):
        """Test SMA when window exceeds data length."""
        series = pd.Series([1.0, 2.0, 3.0])
        result = sma(series, n=10)

        # All values should be NaN
        assert result.isna().all()

    def test_sma_single_element(self):
        """Test SMA with single element."""
        series = pd.Series([100.0])
        result = sma(series, n=1)
        assert result.iloc[0] == 100.0


class TestRSI:
    """Test RSI (Relative Strength Index) calculations."""

    def test_rsi_range(self, sample_ohlcv_data):
        """Test that RSI stays in valid range [0, 100]."""
        close = sample_ohlcv_data['close']
        result = rsi_wilder(close, window=14)

        # Drop NaN values from initial period
        valid_rsi = result.dropna()

        assert (valid_rsi >= 0).all()
        assert (valid_rsi <= 100).all()

    def test_rsi_oversold_condition(self, declining_prices):
        """Test RSI correctly identifies oversold conditions."""
        result = rsi_wilder(declining_prices, window=14)

        # RSI should be low (oversold) for declining prices
        assert result.iloc[-1] < 30

    def test_rsi_overbought_condition(self, rising_prices):
        """Test RSI correctly identifies overbought conditions."""
        result = rsi_wilder(rising_prices, window=14)

        # RSI should be high (overbought) for rising prices
        assert result.iloc[-1] > 70

    def test_rsi_neutral_sideways_market(self, sideways_prices):
        """Test RSI around 50 for sideways market."""
        result = rsi_wilder(sideways_prices, window=14)

        # RSI should be near 50 for neutral market
        assert 30 < result.iloc[-1] < 70

    def test_rsi_default_window(self):
        """Test RSI with default window size."""
        prices = pd.Series(range(1, 31), dtype=float)
        result = rsi_wilder(prices)

        # Should work with default window=14
        assert len(result) == 30
        valid_values = result.dropna()
        assert len(valid_values) > 0


class TestATR:
    """Test Average True Range calculations."""

    def test_atr_basic(self):
        """Test ATR with known values."""
        high = pd.Series([102.0, 103.0, 104.0, 105.0, 106.0])
        low = pd.Series([98.0, 99.0, 100.0, 101.0, 102.0])
        close = pd.Series([100.0, 101.0, 102.0, 103.0, 104.0])

        result = atr(high, low, close, n=3)

        # ATR should always be positive
        assert (result.dropna() > 0).all()

    def test_atr_with_gaps(self):
        """Test ATR correctly handles price gaps."""
        # Simulate gap up on day 3
        high = pd.Series([102.0, 103.0, 114.0, 115.0])
        low = pd.Series([98.0, 99.0, 110.0, 111.0])
        close = pd.Series([100.0, 101.0, 112.0, 113.0])

        result = atr(high, low, close, n=2)

        # ATR should increase after gap (gap contributes to true range)
        assert result.iloc[-1] > result.iloc[1]

    def test_atr_zero_volatility(self):
        """Test ATR with zero volatility (flat prices)."""
        n = 20
        high = pd.Series([100.0] * n)
        low = pd.Series([100.0] * n)
        close = pd.Series([100.0] * n)

        result = atr(high, low, close, n=14)

        # ATR should be zero or very close to zero
        assert result.iloc[-1] < 0.01

    def test_atr_increasing_volatility(self, sample_ohlcv_data):
        """Test ATR responds to volatility in realistic data."""
        result = atr(
            sample_ohlcv_data['high'],
            sample_ohlcv_data['low'],
            sample_ohlcv_data['close'],
            n=14
        )

        # Should have valid values after warmup period
        valid_atr = result.dropna()
        assert len(valid_atr) > 0
        assert (valid_atr > 0).all()


@pytest.mark.unit
class TestIndicatorsEdgeCases:
    """Edge case tests for indicators."""

    def test_sma_with_all_same_values(self):
        """SMA of constant values should equal that constant."""
        series = pd.Series([50.0] * 20)
        result = sma(series, n=5)
        valid = result.dropna()
        assert (valid == 50.0).all()

    def test_rsi_with_all_gains(self):
        """RSI with only gains should approach 100."""
        prices = pd.Series([float(i) for i in range(1, 31)])
        result = rsi_wilder(prices, window=14)
        assert result.iloc[-1] > 90

    def test_rsi_with_all_losses(self):
        """RSI with only losses should approach 0."""
        prices = pd.Series([float(i) for i in range(30, 0, -1)])
        result = rsi_wilder(prices, window=14)
        assert result.iloc[-1] < 10
