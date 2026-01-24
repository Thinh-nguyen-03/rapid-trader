"""Shared pytest fixtures for RapidTrader tests."""
import pytest
import pandas as pd
import numpy as np
from datetime import date, timedelta
import random


@pytest.fixture(scope="session")
def test_db_url():
    """Test database URL (uses in-memory SQLite for speed)."""
    return "sqlite:///:memory:"


@pytest.fixture
def sample_ohlcv_data():
    """Provide sample OHLCV data for testing indicators."""
    np.random.seed(42)
    dates = pd.date_range(start='2023-01-01', periods=100, freq='D')

    # Generate realistic price data with random walk
    base_price = 100.0
    prices = [base_price]

    for _ in range(99):
        change = prices[-1] * 0.02 * (2 * (np.random.random() - 0.5))
        prices.append(max(prices[-1] + change, 1.0))

    return pd.DataFrame({
        'open': [p * (1 + np.random.uniform(-0.01, 0.01)) for p in prices],
        'high': [p * (1 + np.random.uniform(0, 0.02)) for p in prices],
        'low': [p * (1 - np.random.uniform(0, 0.02)) for p in prices],
        'close': prices,
        'volume': [1000000 + np.random.randint(-100000, 100000) for _ in range(100)]
    }, index=dates)


@pytest.fixture
def declining_prices():
    """Create a consistently declining price series."""
    return pd.Series([100, 95, 90, 85, 80, 75, 70, 65, 60, 55, 50,
                     48, 46, 44, 42, 40, 38, 36, 34, 32, 30])


@pytest.fixture
def rising_prices():
    """Create a consistently rising price series."""
    return pd.Series([50, 52, 54, 56, 58, 60, 62, 64, 66, 68, 70,
                     72, 74, 76, 78, 80, 82, 84, 86, 88, 90])


@pytest.fixture
def sideways_prices():
    """Create a sideways/oscillating price series."""
    return pd.Series([100, 102, 98, 101, 99, 100, 102, 98, 101, 99,
                     100, 102, 98, 101, 99, 100, 102, 98, 101, 99])
