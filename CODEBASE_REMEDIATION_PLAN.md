# RapidTrader Codebase Remediation Plan

**Document Version:** 1.0
**Created:** 2025-11-01
**Reviewer:** Senior Engineering Review
**Status:** Ready for Implementation

---

## 📋 Executive Summary

This document outlines a comprehensive plan to elevate RapidTrader from prototype-quality (3/10) to production-ready (8/10) code suitable for technical interviews at FAANG/hedge fund/quant firms.

**Total Estimated Time:** 6-8 weeks
**Critical Issues:** 6
**High Priority Issues:** 9
**Medium Priority Issues:** 5

---

## 🎯 Implementation Strategy

Issues are organized by:
1. **Difficulty:** Easy → Medium → Hard
2. **Time Required:** Hours → Days → Weeks
3. **Dependencies:** What must be done first

---

# PHASE 1: CRITICAL FIXES (Must Do First)

These are blocking issues that would cause immediate rejection in code review.

---

## ✅ ISSUE #1: Fix SQL Injection Vulnerabilities

**Severity:** CRITICAL
**Difficulty:** Easy
**Time Required:** 2-4 hours
**Files Affected:** `scripts/update_database.py`, `rapidtrader/data/ingest.py`

### Problem
Using f-strings and manual escaping in SQL queries exposes the system to SQL injection attacks.

**Bad Code (Current):**
```python
# scripts/update_database.py:55-61
clean_sector_escaped = clean_sector.replace("'", "''")
conn.execute(text(f"""
    INSERT INTO symbols (symbol, sector, is_active)
    VALUES ('{symbol}', '{clean_sector_escaped}', true)
    ON CONFLICT (symbol) DO UPDATE SET sector = '{clean_sector_escaped}'
"""))
```

### Solution Steps

**Step 1:** Fix `scripts/update_database.py`

Replace lines 49-61:
```python
# BEFORE (lines 49-61)
for symbol, sector in symbols:
    clean_sector = map_sector_name(sector)
    clean_sector_escaped = clean_sector.replace("'", "''")

    conn.execute(text(f"""
        INSERT INTO symbols (symbol, sector, is_active)
        VALUES ('{symbol}', '{clean_sector_escaped}', true)
        ON CONFLICT (symbol) DO UPDATE SET
            sector = '{clean_sector_escaped}',
            is_active = true
    """))

# AFTER
for symbol, sector in symbols:
    clean_sector = map_sector_name(sector)

    conn.execute(text("""
        INSERT INTO symbols (symbol, sector, is_active)
        VALUES (:symbol, :sector, true)
        ON CONFLICT (symbol) DO UPDATE SET
            sector = EXCLUDED.sector,
            is_active = true
    """), {"symbol": symbol, "sector": clean_sector})
```

**Step 2:** Fix `scripts/update_database.py` lines 188-203

Replace the entire batch_data loop:
```python
# BEFORE (lines 186-203)
for data in batch_data:
    symbol = data["symbol"].replace("'", "''")
    sector = data["sector"].replace("'", "''")
    sic_description = data["sic_description"].replace("'", "''")
    sic_code = data["sic_code"] if data["sic_code"] is not None else "NULL"

    conn.execute(text(f"""
        INSERT INTO sector_cache (symbol, sector, sic_description, sic_code, last_updated)
        VALUES ('{symbol}', '{sector}', '{sic_description}', {sic_code}, CURRENT_DATE)
        ...
    """))

# AFTER
for data in batch_data:
    conn.execute(text("""
        INSERT INTO sector_cache (symbol, sector, sic_description, sic_code, last_updated)
        VALUES (:symbol, :sector, :sic_description, :sic_code, CURRENT_DATE)
        ON CONFLICT (symbol) DO UPDATE SET
            sector = EXCLUDED.sector,
            sic_description = EXCLUDED.sic_description,
            sic_code = EXCLUDED.sic_code,
            last_updated = CURRENT_DATE
    """), {
        "symbol": data["symbol"],
        "sector": data["sector"],
        "sic_description": data["sic_description"],
        "sic_code": data["sic_code"]
    })
```

**Step 3:** Search for other f-string SQL patterns
```bash
cd /home/user/rapid-trader
grep -rn "text(f\"" --include="*.py"
grep -rn 'text(f"' --include="*.py"
```

Fix any additional instances using the same pattern.

### Validation
```python
# Test with malicious input
symbol = "AAPL'; DROP TABLE symbols; --"
# Should be safely escaped by parameterization
```

---

## ✅ ISSUE #2: Remove Mock Data from Production Code

**Severity:** CRITICAL
**Difficulty:** Medium
**Time Required:** 4-6 hours
**Files Affected:** `rapidtrader/risk/kill_switch.py`

### Problem
The kill switch uses random fake data instead of real P&L calculations, making it completely unreliable.

**Bad Code (Current):**
```python
# rapidtrader/risk/kill_switch.py:72-86
def compute_daily_returns_from_orders(eng, lookback_days: int = 60) -> pd.Series:
    # MVP: Simple proxy for returns
    np.random.seed(42)  # FAKE DATA!
    base_return = np.random.normal(0.001, 0.02)
    returns_data[trade_date] = base_return
```

### Solution Steps

**Step 1:** Create a new function for real P&L calculation

Add to `rapidtrader/risk/kill_switch.py`:
```python
def compute_daily_pnl_from_fills(eng, lookback_days: int = 60) -> pd.Series:
    """Compute actual daily P&L from execution fills.

    This calculates real profit/loss using entry and exit prices from fills.

    Args:
        eng: Database engine
        lookback_days: Number of days to look back

    Returns:
        Series of daily P&L in dollars, indexed by date
    """
    cutoff_date = date.today() - timedelta(days=lookback_days)

    # Get all fills (buys and sells) with actual execution prices
    query = text("""
        WITH position_pnl AS (
            SELECT
                exit_fill.d AS exit_date,
                exit_fill.symbol,
                entry_fill.avg_px AS entry_price,
                exit_fill.avg_px AS exit_price,
                exit_fill.qty AS quantity
            FROM exec_fills AS exit_fill
            INNER JOIN exec_fills AS entry_fill
                ON exit_fill.symbol = entry_fill.symbol
                AND entry_fill.side = 'buy'
                AND exit_fill.side = 'sell'
                AND entry_fill.d < exit_fill.d
            WHERE exit_fill.d >= :cutoff
                AND exit_fill.side IN ('sell', 'exit')
        )
        SELECT
            exit_date,
            SUM((exit_price - entry_price) * quantity) AS daily_pnl
        FROM position_pnl
        GROUP BY exit_date
        ORDER BY exit_date
    """)

    df = pd.read_sql(query, eng, params={"cutoff": cutoff_date}, parse_dates=["exit_date"])

    if df.empty:
        return pd.Series(dtype=float, name="pnl")

    pnl_series = df.set_index("exit_date")["daily_pnl"]
    pnl_series.index.name = "date"

    return pnl_series


def compute_daily_returns_from_pnl(eng, lookback_days: int = 60) -> pd.Series:
    """Convert P&L to percentage returns.

    Returns = Daily P&L / Portfolio Value
    """
    pnl = compute_daily_pnl_from_fills(eng, lookback_days)

    if pnl.empty:
        return pd.Series(dtype=float, name="returns")

    # Get portfolio value for each date (simplified: use starting capital)
    # TODO: Track actual portfolio value over time in database
    portfolio_value = settings.RT_START_CAPITAL

    returns = pnl / portfolio_value
    returns.name = "returns"

    return returns
```

**Step 2:** Update `compute_losing_streak` to use real data

Replace the function (lines 89-130):
```python
def compute_losing_streak(eng, lookback_days: int = 90) -> int:
    """Compute current losing streak from actual trade P&L.

    Args:
        eng: Database engine
        lookback_days: Number of days to analyze

    Returns:
        Number of consecutive losing trades
    """
    cutoff_date = date.today() - timedelta(days=lookback_days)

    # Get recent exit fills with actual P&L
    query = text("""
        WITH trade_pnl AS (
            SELECT
                exit_fill.d AS exit_date,
                exit_fill.symbol,
                (exit_fill.avg_px - entry_fill.avg_px) * exit_fill.qty AS pnl
            FROM exec_fills AS exit_fill
            INNER JOIN exec_fills AS entry_fill
                ON exit_fill.symbol = entry_fill.symbol
                AND entry_fill.side = 'buy'
                AND exit_fill.side IN ('sell', 'exit')
                AND entry_fill.d < exit_fill.d
            WHERE exit_fill.d >= :cutoff
            ORDER BY exit_fill.d DESC
        )
        SELECT exit_date, symbol, pnl
        FROM trade_pnl
        ORDER BY exit_date DESC
    """)

    df = pd.read_sql(query, eng, params={"cutoff": cutoff_date}, parse_dates=["exit_date"])

    if df.empty:
        return 0

    # Count consecutive losses from most recent trade
    streak = 0
    for _, row in df.iterrows():
        if row["pnl"] < 0:
            streak += 1
        else:
            break  # Streak broken by a win

    return streak
```

**Step 3:** Update `evaluate_kill_switch` to use new functions

Replace line 150:
```python
# BEFORE
returns = compute_daily_returns_from_orders(eng, lookback_days)

# AFTER
returns = compute_daily_returns_from_pnl(eng, lookback_days)
```

**Step 4:** Add fallback for when no fills exist yet

```python
def compute_daily_returns_from_pnl(eng, lookback_days: int = 60) -> pd.Series:
    """Convert P&L to percentage returns."""
    pnl = compute_daily_pnl_from_fills(eng, lookback_days)

    if pnl.empty:
        # No fills yet - return empty series (kill switch will be inactive)
        print("INFO: No execution fills found - kill switch evaluation skipped")
        return pd.Series(dtype=float, name="returns")

    # ... rest of function
```

### Validation
```python
# Test that it returns real data
eng = get_engine()
returns = compute_daily_returns_from_pnl(eng, 30)
assert not any(returns == 0.001)  # Should not have the fake constant
```

---

## ✅ ISSUE #3: Fix Global Mutable State & Thread Safety

**Severity:** CRITICAL
**Difficulty:** Medium
**Time Required:** 3-4 hours
**Files Affected:** `rapidtrader/core/db.py`

### Problem
Global `_engine` variable causes race conditions and prevents proper testing/multi-connection scenarios.

### Solution Steps

**Step 1:** Replace singleton pattern with connection pooling

Replace entire `rapidtrader/core/db.py`:
```python
"""Database connection management for RapidTrader.

Uses SQLAlchemy connection pooling for thread-safe database access.
"""
from sqlalchemy import create_engine, Engine, pool
from sqlalchemy.orm import Session, sessionmaker
from contextlib import contextmanager
from typing import Generator
from .config import settings


class DatabaseManager:
    """Thread-safe database connection manager."""

    def __init__(self, db_url: str | None = None):
        """Initialize database manager with connection pooling.

        Args:
            db_url: Database connection URL (defaults to settings.RT_DB_URL)
        """
        self._db_url = db_url or settings.RT_DB_URL
        self._engine: Engine | None = None
        self._session_factory: sessionmaker | None = None

    @property
    def engine(self) -> Engine:
        """Get or create database engine with connection pooling."""
        if self._engine is None:
            self._engine = create_engine(
                self._db_url,
                poolclass=pool.QueuePool,
                pool_size=10,          # Maximum connections to keep open
                max_overflow=20,       # Allow 20 additional connections under load
                pool_pre_ping=True,    # Verify connections before using
                pool_recycle=3600,     # Recycle connections after 1 hour
                echo=False
            )
        return self._engine

    @property
    def session_factory(self) -> sessionmaker:
        """Get or create session factory."""
        if self._session_factory is None:
            self._session_factory = sessionmaker(
                bind=self.engine,
                autocommit=False,
                autoflush=False
            )
        return self._session_factory

    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """Context manager for database sessions.

        Usage:
            with db_manager.get_session() as session:
                results = session.execute(query)
        """
        session = self.session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def dispose(self):
        """Close all connections in the pool."""
        if self._engine is not None:
            self._engine.dispose()
            self._engine = None
            self._session_factory = None


# Global instance for application use
_db_manager = DatabaseManager()


def get_engine() -> Engine:
    """Get the database engine.

    This function maintains backward compatibility with existing code.
    Thread-safe due to connection pooling in the engine.

    Returns:
        SQLAlchemy Engine instance with connection pooling
    """
    return _db_manager.engine


def get_session() -> Generator[Session, None, None]:
    """Get a database session context manager.

    Usage:
        with get_session() as session:
            results = session.execute(query)

    Yields:
        SQLAlchemy Session instance
    """
    return _db_manager.get_session()


def dispose_engine():
    """Dispose of the database engine and close all connections.

    Useful for testing or application shutdown.
    """
    _db_manager.dispose()


# For testing: allow injection of different database
def set_test_database(db_url: str):
    """Set a different database URL for testing.

    Args:
        db_url: Test database connection URL
    """
    global _db_manager
    _db_manager.dispose()  # Close existing connections
    _db_manager = DatabaseManager(db_url)
```

**Step 2:** Update `rapidtrader/data/ingest.py` to use connection pooling properly

The existing code actually works fine with connection pooling since each thread creates its own client. No changes needed, but add a comment:

```python
# Line 194: Add comment
db_lock = threading.Lock()  # Protects database writes (connections are pooled)
```

**Step 3:** Update imports across codebase (optional for backward compatibility)

The new `get_engine()` function maintains the same interface, so existing code continues to work.

### Validation
```python
# Test thread safety
import concurrent.futures

def test_concurrent_connections():
    def query_db(i):
        eng = get_engine()
        with eng.connect() as conn:
            result = conn.execute(text("SELECT 1")).scalar()
            return result == 1

    with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
        results = list(executor.map(query_db, range(100)))

    assert all(results)  # All queries should succeed
```

---

## ✅ ISSUE #4: Add Structured Logging

**Severity:** CRITICAL
**Difficulty:** Easy
**Time Required:** 3-4 hours
**Files Affected:** All Python files

### Problem
Using `print()` statements means logs vanish in production, can't be aggregated, and have no severity levels.

### Solution Steps

**Step 1:** Add logging dependencies

Update `pyproject.toml`:
```toml
[project]
dependencies = [
    "pandas>=2.2",
    "numpy>=1.26",
    "SQLAlchemy>=2.0",
    "psycopg[binary]>=3.2",
    "pydantic-settings>=2.4",
    "python-dotenv>=1.0",
    "alpaca-py>=0.21",
    "pandas-market-calendars>=4.4",
    "polygon-api-client>=1.14.0",
    "structlog>=23.1.0",      # NEW: Structured logging
    "python-json-logger>=2.0"  # NEW: JSON formatter
]
```

**Step 2:** Create logging configuration module

Create `rapidtrader/core/logging_config.py`:
```python
"""Centralized logging configuration for RapidTrader."""
import logging
import sys
from pathlib import Path
import structlog
from pythonjsonlogger import jsonlogger


def setup_logging(
    log_level: str = "INFO",
    json_logs: bool = False,
    log_file: Path | None = None
) -> None:
    """Configure structured logging for the application.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_logs: If True, output JSON format (for production)
        log_file: Optional file path for log output
    """
    # Configure standard logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper()),
    )

    # Processors for structlog
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    if json_logs:
        # Production: JSON output
        processors.append(structlog.processors.JSONRenderer())
    else:
        # Development: Human-readable output
        processors.extend([
            structlog.dev.ConsoleRenderer(colors=True),
        ])

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # File handler if specified
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file)

        if json_logs:
            formatter = jsonlogger.JsonFormatter(
                '%(asctime)s %(name)s %(levelname)s %(message)s'
            )
        else:
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )

        file_handler.setFormatter(formatter)
        logging.root.addHandler(file_handler)


def get_logger(name: str) -> structlog.BoundLogger:
    """Get a logger instance for a module.

    Args:
        name: Logger name (usually __name__)

    Returns:
        Configured logger instance
    """
    return structlog.get_logger(name)
```

**Step 3:** Update config to include logging settings

Add to `rapidtrader/core/config.py`:
```python
class Settings(BaseSettings):
    # ... existing settings ...

    # Logging
    RT_LOG_LEVEL: str = "INFO"
    RT_LOG_JSON: bool = False  # True for production
    RT_LOG_FILE: str = ""  # Optional log file path
```

**Step 4:** Replace print() statements - Example in `eod_ingest.py`

```python
# At top of file
from ..core.logging_config import get_logger

logger = get_logger(__name__)

# Replace print statements:

# BEFORE:
print("Starting EOD data ingestion job...")
print(f"Found {len(symbols)} active symbols to update")
print(f"ERROR: No active symbols found in database")

# AFTER:
logger.info("starting_eod_ingestion", job="eod_ingest")
logger.info("found_active_symbols", count=len(symbols), job="eod_ingest")
logger.error("no_active_symbols", job="eod_ingest")
```

**Step 5:** Initialize logging in job entry points

```python
# rapidtrader/jobs/eod_ingest.py
from ..core.logging_config import setup_logging, get_logger
from ..core.config import settings

def main():
    # Initialize logging first
    setup_logging(
        log_level=settings.RT_LOG_LEVEL,
        json_logs=settings.RT_LOG_JSON,
        log_file=Path(settings.RT_LOG_FILE) if settings.RT_LOG_FILE else None
    )

    logger = get_logger(__name__)

    try:
        logger.info("job_started", job="eod_ingest", args=vars(args))
        # ... rest of function
    except Exception as e:
        logger.exception("job_failed", job="eod_ingest", error=str(e))
        return 1
```

**Step 6:** Systematically replace print() across codebase

Create a script to help identify all print statements:
```bash
grep -rn "print(" rapidtrader/ --include="*.py" | grep -v "# print" > print_statements.txt
```

Replace following the pattern:
- `print(f"ERROR: ...")` → `logger.error(...)`
- `print(f"WARNING: ...")` → `logger.warning(...)`
- `print(f"INFO: ...")` → `logger.info(...)`
- `print(f"SUCCESS: ...")` → `logger.info(..., status="success")`

### Validation
```python
# Test that logs are structured
import json

# Run a job and capture output
# Verify logs are valid JSON in production mode
```

---

# PHASE 2: HIGH PRIORITY FIXES (Week 1-2)

---

## ✅ ISSUE #5: Add Comprehensive Test Suite

**Severity:** HIGH
**Difficulty:** Hard
**Time Required:** 2-3 weeks (can be done incrementally)
**Dependencies:** None (but easier after fixing other issues)

### Problem
Zero test coverage is an automatic rejection at any serious company.

### Solution Steps

**Step 1:** Add testing dependencies

Update `pyproject.toml`:
```toml
[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "pytest-cov>=4.1.0",
    "pytest-asyncio>=0.21.0",
    "pytest-mock>=3.11.0",
    "hypothesis>=6.82.0",      # Property-based testing
    "faker>=19.2.0",            # Fake data generation
    "freezegun>=1.2.2",         # Time mocking
]
```

**Step 2:** Create test infrastructure

```bash
mkdir -p tests/{unit,integration,e2e}
touch tests/__init__.py
touch tests/conftest.py
```

**Step 3:** Create pytest configuration

Create `pytest.ini`:
```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts =
    --verbose
    --cov=rapidtrader
    --cov-report=html
    --cov-report=term-missing
    --cov-fail-under=70
markers =
    unit: Unit tests (fast, no external dependencies)
    integration: Integration tests (require database)
    slow: Slow tests
    e2e: End-to-end tests
```

**Step 4:** Create test fixtures

Create `tests/conftest.py`:
```python
"""Shared pytest fixtures for RapidTrader tests."""
import pytest
import pandas as pd
from datetime import date, timedelta
from sqlalchemy import create_engine, text
from rapidtrader.core.db import set_test_database, dispose_engine
from rapidtrader.core.config import Settings


@pytest.fixture(scope="session")
def test_db_url():
    """Test database URL (uses in-memory SQLite for speed)."""
    return "sqlite:///:memory:"


@pytest.fixture(scope="function")
def db_engine(test_db_url):
    """Provide a clean database engine for each test."""
    set_test_database(test_db_url)

    from rapidtrader.core.db import get_engine
    engine = get_engine()

    # Create tables
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS symbols (
                symbol VARCHAR(10) PRIMARY KEY,
                sector VARCHAR(50),
                is_active BOOLEAN DEFAULT true
            )
        """))

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS bars_daily (
                symbol VARCHAR(10),
                d DATE,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                volume INTEGER,
                PRIMARY KEY (symbol, d)
            )
        """))

        # Add other tables as needed

    yield engine

    # Cleanup
    dispose_engine()


@pytest.fixture
def sample_ohlcv_data():
    """Provide sample OHLCV data for testing indicators."""
    dates = pd.date_range(start='2023-01-01', periods=100, freq='D')

    # Generate realistic price data
    base_price = 100.0
    prices = [base_price]

    for _ in range(99):
        change = prices[-1] * 0.02 * (2 * (0.5 - random.random()))
        prices.append(prices[-1] + change)

    return pd.DataFrame({
        'date': dates,
        'open': [p * 0.99 for p in prices],
        'high': [p * 1.02 for p in prices],
        'low': [p * 0.98 for p in prices],
        'close': prices,
        'volume': [1000000 + random.randint(-100000, 100000) for _ in range(100)]
    }).set_index('date')


@pytest.fixture
def mock_polygon_client(mocker):
    """Mock Polygon.io API client."""
    mock = mocker.Mock()
    mock.get_daily_bars.return_value = pd.DataFrame({
        'open': [100, 101, 102],
        'high': [102, 103, 104],
        'low': [99, 100, 101],
        'close': [101, 102, 103],
        'volume': [1000000, 1100000, 1200000]
    })
    return mock
```

**Step 5:** Write unit tests for indicators

Create `tests/unit/test_indicators.py`:
```python
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
        series = pd.Series([1, 2, np.nan, 4, 5])
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
        series = pd.Series([1, 2, 3])
        result = sma(series, n=10)

        # All values should be NaN
        assert result.isna().all()


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

    def test_rsi_oversold_condition(self):
        """Test RSI correctly identifies oversold conditions."""
        # Create declining price series
        prices = pd.Series([100, 95, 90, 85, 80, 75, 70, 65, 60, 55, 50,
                           48, 46, 44, 42, 40, 38, 36, 34, 32, 30])

        result = rsi_wilder(prices, window=14)

        # RSI should be low (oversold) for declining prices
        assert result.iloc[-1] < 30

    def test_rsi_overbought_condition(self):
        """Test RSI correctly identifies overbought conditions."""
        # Create rising price series
        prices = pd.Series([50, 52, 54, 56, 58, 60, 62, 64, 66, 68, 70,
                           72, 74, 76, 78, 80, 82, 84, 86, 88, 90])

        result = rsi_wilder(prices, window=14)

        # RSI should be high (overbought) for rising prices
        assert result.iloc[-1] > 70

    def test_rsi_neutral_sideways_market(self):
        """Test RSI around 50 for sideways market."""
        # Oscillating prices
        prices = pd.Series([100, 102, 98, 101, 99, 100, 102, 98, 101, 99,
                           100, 102, 98, 101, 99, 100, 102, 98, 101, 99])

        result = rsi_wilder(prices, window=14)

        # RSI should be near 50 for neutral market
        assert 40 < result.iloc[-1] < 60


class TestATR:
    """Test Average True Range calculations."""

    def test_atr_basic(self):
        """Test ATR with known values."""
        high = pd.Series([102, 103, 104, 105, 106])
        low = pd.Series([98, 99, 100, 101, 102])
        close = pd.Series([100, 101, 102, 103, 104])

        result = atr(high, low, close, n=3)

        # ATR should always be positive
        assert (result.dropna() > 0).all()

    def test_atr_with_gaps(self):
        """Test ATR correctly handles price gaps."""
        # Simulate gap up
        high = pd.Series([102, 103, 114, 115])
        low = pd.Series([98, 99, 110, 111])
        close = pd.Series([100, 101, 112, 113])

        result = atr(high, low, close, n=2)

        # ATR should increase after gap
        assert result.iloc[2] > result.iloc[1]

    def test_atr_zero_volatility(self):
        """Test ATR with zero volatility (flat prices)."""
        high = pd.Series([100] * 20)
        low = pd.Series([100] * 20)
        close = pd.Series([100] * 20)

        result = atr(high, low, close, n=14)

        # ATR should be zero or very close to zero
        assert result.iloc[-1] < 0.01


# Property-based testing with Hypothesis
from hypothesis import given, strategies as st

class TestIndicatorsProperties:
    """Property-based tests for indicators."""

    @given(st.lists(st.floats(min_value=0.01, max_value=1000), min_size=30, max_size=100))
    def test_sma_never_exceeds_bounds(self, prices):
        """SMA should always be between min and max of window."""
        series = pd.Series(prices)
        result = sma(series, n=10)

        for i in range(10, len(series)):
            window_values = series.iloc[i-9:i+1]
            assert window_values.min() <= result.iloc[i] <= window_values.max()

    @given(st.lists(st.floats(min_value=1, max_value=1000), min_size=30, max_size=100))
    def test_rsi_always_in_range(self, prices):
        """RSI must always be between 0 and 100."""
        series = pd.Series(prices)
        result = rsi_wilder(series, window=14)

        valid_values = result.dropna()
        assert (valid_values >= 0).all()
        assert (valid_values <= 100).all()
```

**Step 6:** Write tests for position sizing

Create `tests/unit/test_position_sizing.py`:
```python
"""Unit tests for position sizing algorithms."""
import pytest
from rapidtrader.risk.sizing import shares_fixed_fractional, shares_atr_target


class TestFixedFractionalSizing:
    """Test fixed fractional position sizing."""

    def test_basic_calculation(self):
        """Test basic position size calculation."""
        result = shares_fixed_fractional(
            portfolio_value=100000,
            pct_per_trade=0.05,
            entry_px=50.0
        )

        # $100k * 5% / $50 = 100 shares
        assert result == 100

    def test_rounds_down(self):
        """Test that fractional shares are rounded down."""
        result = shares_fixed_fractional(
            portfolio_value=100000,
            pct_per_trade=0.05,
            entry_px=51.0
        )

        # $100k * 5% / $51 = 98.039... → 98 shares
        assert result == 98

    def test_expensive_stock(self):
        """Test with expensive stock price."""
        result = shares_fixed_fractional(
            portfolio_value=100000,
            pct_per_trade=0.05,
            entry_px=5000.0
        )

        # $100k * 5% / $5000 = 1 share
        assert result == 1

    def test_negative_portfolio_raises_error(self):
        """Test that negative portfolio value raises error."""
        # NOTE: This test will fail with current implementation!
        # This is intentional - it shows the bug we need to fix
        with pytest.raises(ValueError, match="Portfolio value must be positive"):
            shares_fixed_fractional(
                portfolio_value=-100000,
                pct_per_trade=0.05,
                entry_px=50.0
            )

    def test_invalid_percentage_raises_error(self):
        """Test that invalid percentage raises error."""
        with pytest.raises(ValueError, match="pct_per_trade must be in"):
            shares_fixed_fractional(
                portfolio_value=100000,
                pct_per_trade=1.5,  # 150% is invalid
                entry_px=50.0
            )

    def test_zero_price_raises_error(self):
        """Test that zero price raises error."""
        with pytest.raises(ValueError, match="Entry price must be positive"):
            shares_fixed_fractional(
                portfolio_value=100000,
                pct_per_trade=0.05,
                entry_px=0.0
            )


class TestATRTargetSizing:
    """Test ATR-based volatility targeting."""

    def test_basic_calculation(self):
        """Test basic ATR target calculation."""
        result = shares_atr_target(
            portfolio_value=100000,
            daily_risk_cap=0.005,
            atr_points=2.0,
            k_atr=3.0
        )

        # Risk budget: $100k * 0.5% = $500
        # Unit risk: 3.0 * $2.0 = $6
        # Shares: $500 / $6 = 83.33... → 83 shares
        assert result == 83

    def test_high_volatility_reduces_size(self):
        """Test that higher volatility reduces position size."""
        low_vol = shares_atr_target(100000, 0.005, atr_points=1.0, k_atr=3.0)
        high_vol = shares_atr_target(100000, 0.005, atr_points=5.0, k_atr=3.0)

        assert high_vol < low_vol

    def test_larger_risk_budget_increases_size(self):
        """Test that larger risk budget increases position size."""
        small_risk = shares_atr_target(100000, 0.001, atr_points=2.0, k_atr=3.0)
        large_risk = shares_atr_target(100000, 0.01, atr_points=2.0, k_atr=3.0)

        assert large_risk > small_risk
```

**Step 7:** Write integration tests

Create `tests/integration/test_database_operations.py`:
```python
"""Integration tests for database operations."""
import pytest
from datetime import date
from sqlalchemy import text
from rapidtrader.data.ingest import upsert_bars
import pandas as pd


@pytest.mark.integration
class TestDatabaseIntegration:
    """Test database read/write operations."""

    def test_upsert_bars_insert(self, db_engine):
        """Test inserting new bars."""
        bars = pd.DataFrame({
            'Open': [100.0, 101.0],
            'High': [102.0, 103.0],
            'Low': [99.0, 100.0],
            'Close': [101.0, 102.0],
            'Volume': [1000000, 1100000]
        }, index=[date(2023, 1, 1), date(2023, 1, 2)])

        upsert_bars('AAPL', bars)

        # Verify data was inserted
        with db_engine.connect() as conn:
            result = conn.execute(text("""
                SELECT COUNT(*) FROM bars_daily WHERE symbol = 'AAPL'
            """)).scalar()

            assert result == 2

    def test_upsert_bars_update(self, db_engine):
        """Test updating existing bars."""
        # Insert initial data
        bars_v1 = pd.DataFrame({
            'Open': [100.0],
            'High': [102.0],
            'Low': [99.0],
            'Close': [101.0],
            'Volume': [1000000]
        }, index=[date(2023, 1, 1)])

        upsert_bars('AAPL', bars_v1)

        # Update with revised data
        bars_v2 = pd.DataFrame({
            'Open': [100.5],  # Changed
            'High': [102.5],
            'Low': [99.5],
            'Close': [101.5],
            'Volume': [1100000]  # Changed
        }, index=[date(2023, 1, 1)])

        upsert_bars('AAPL', bars_v2)

        # Verify updated
        with db_engine.connect() as conn:
            result = conn.execute(text("""
                SELECT close, volume FROM bars_daily
                WHERE symbol = 'AAPL' AND d = '2023-01-01'
            """)).first()

            assert result[0] == 101.5
            assert result[1] == 1100000
```

**Step 8:** Set up continuous testing

Create `.github/workflows/tests.yml`:
```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v3

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'

    - name: Install dependencies
      run: |
        pip install -e .[dev]

    - name: Run tests
      run: |
        pytest --cov=rapidtrader --cov-report=xml

    - name: Upload coverage
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
```

### Testing Roadmap
1. **Week 1:** Unit tests for indicators, sizing, confirmation (20 hours)
2. **Week 2:** Integration tests for database, API clients (15 hours)
3. **Week 3:** E2E tests for job workflows (10 hours)

**Target:** 70%+ code coverage before considering project "interview ready"

---

## ✅ ISSUE #6: Add Input Validation with Pydantic

**Severity:** HIGH
**Difficulty:** Medium
**Time Required:** 8-12 hours
**Dependencies:** None

### Problem
Functions silently accept invalid inputs, making bugs hard to detect.

### Solution Steps

**Step 1:** Create domain models with validation

Create `rapidtrader/core/models.py`:
```python
"""Domain models with validation for RapidTrader."""
from pydantic import BaseModel, Field, validator, root_validator
from datetime import date
from typing import Literal
from decimal import Decimal


class TradingSymbol(BaseModel):
    """Validated trading symbol."""

    symbol: str = Field(..., regex="^[A-Z]{1,5}$", description="Stock ticker symbol")
    sector: str = Field(..., min_length=1, max_length=50)
    is_active: bool = True

    class Config:
        frozen = True  # Immutable


class OHLCVBar(BaseModel):
    """Validated OHLCV bar data."""

    symbol: str = Field(..., regex="^[A-Z]{1,5}$")
    date: date
    open: Decimal = Field(..., gt=0, description="Opening price")
    high: Decimal = Field(..., gt=0, description="High price")
    low: Decimal = Field(..., gt=0, description="Low price")
    close: Decimal = Field(..., gt=0, description="Closing price")
    volume: int = Field(..., ge=0, description="Trading volume")

    @root_validator
    def validate_prices(cls, values):
        """Validate price relationships."""
        high = values.get('high')
        low = values.get('low')
        open_price = values.get('open')
        close = values.get('close')

        if high and low and high < low:
            raise ValueError(f"High ({high}) cannot be less than low ({low})")

        if high and open_price and open_price > high:
            raise ValueError(f"Open ({open_price}) cannot exceed high ({high})")

        if high and close and close > high:
            raise ValueError(f"Close ({close}) cannot exceed high ({high})")

        if low and open_price and open_price < low:
            raise ValueError(f"Open ({open_price}) cannot be below low ({low})")

        if low and close and close < low:
            raise ValueError(f"Close ({close}) cannot be below low ({low})")

        return values


class PositionSizeRequest(BaseModel):
    """Request for position sizing calculation."""

    portfolio_value: Decimal = Field(..., gt=0, description="Total portfolio value")
    pct_per_trade: Decimal = Field(..., gt=0, lt=1, description="Percentage per trade")
    entry_price: Decimal = Field(..., gt=0, description="Entry price")

    class Config:
        validate_assignment = True


class ATRSizeRequest(BaseModel):
    """Request for ATR-based position sizing."""

    portfolio_value: Decimal = Field(..., gt=0)
    daily_risk_cap: Decimal = Field(..., gt=0, lt=0.1, description="Max 10% daily risk")
    atr_points: Decimal = Field(..., gt=0)
    k_atr: Decimal = Field(3.0, gt=0, le=10, description="ATR multiplier")

    class Config:
        validate_assignment = True


class TradingSignal(BaseModel):
    """Validated trading signal."""

    symbol: str = Field(..., regex="^[A-Z]{1,5}$")
    date: date
    strategy: Literal['RSI_MR', 'SMA_X', 'COMBINED']
    direction: Literal['buy', 'sell', 'hold']
    strength: float = Field(..., ge=0.0, le=1.0, description="Signal strength")

    class Config:
        frozen = True


class OrderRequest(BaseModel):
    """Validated order request."""

    symbol: str = Field(..., regex="^[A-Z]{1,5}$")
    date: date
    side: Literal['buy', 'sell', 'exit']
    quantity: int = Field(..., ge=0, description="Number of shares")
    order_type: Literal['market', 'limit'] = 'market'
    reason: str = Field(..., min_length=1, max_length=100)

    @validator('quantity')
    def validate_quantity(cls, v, values):
        """Validate quantity based on side."""
        side = values.get('side')

        if side == 'buy' and v == 0:
            raise ValueError("Buy orders must have quantity > 0")

        # exit orders can have 0 quantity (means close full position)

        return v
```

**Step 2:** Update position sizing functions to use validation

Update `rapidtrader/risk/sizing.py`:
```python
"""Position sizing algorithms for RapidTrader."""
import math
from decimal import Decimal
from ..core.models import PositionSizeRequest, ATRSizeRequest


def shares_fixed_fractional(
    portfolio_value: float,
    pct_per_trade: float,
    entry_px: float
) -> int:
    """Calculate position size using fixed-fractional method.

    Args:
        portfolio_value: Total portfolio value in dollars
        pct_per_trade: Percentage of portfolio to risk per trade (0.0-1.0)
        entry_px: Expected entry price per share

    Returns:
        Number of shares to purchase (integer)

    Raises:
        ValidationError: If inputs are invalid

    Examples:
        >>> shares_fixed_fractional(100000, 0.05, 50.0)
        100  # $100k * 5% / $50 = 100 shares
    """
    # Validate inputs using Pydantic model
    request = PositionSizeRequest(
        portfolio_value=Decimal(str(portfolio_value)),
        pct_per_trade=Decimal(str(pct_per_trade)),
        entry_price=Decimal(str(entry_px))
    )

    # Calculate position value
    position_value = float(request.portfolio_value * request.pct_per_trade)

    # Calculate number of shares (floor to integer)
    shares = math.floor(position_value / float(request.entry_price))

    return max(0, shares)


def shares_atr_target(
    portfolio_value: float,
    daily_risk_cap: float,
    atr_points: float,
    k_atr: float = 3.0
) -> int:
    """Calculate position size using ATR-based volatility targeting.

    Args:
        portfolio_value: Total portfolio value in dollars
        daily_risk_cap: Maximum daily risk as fraction of portfolio (0.0-0.1)
        atr_points: Average True Range in price points
        k_atr: ATR multiplier for stop distance (default 3.0)

    Returns:
        Number of shares to purchase (integer)

    Raises:
        ValidationError: If inputs are invalid

    Examples:
        >>> shares_atr_target(100000, 0.005, 2.0, 3.0)
        83  # $100k * 0.5% / (3.0 * $2.0) = 83 shares
    """
    # Validate inputs
    request = ATRSizeRequest(
        portfolio_value=Decimal(str(portfolio_value)),
        daily_risk_cap=Decimal(str(daily_risk_cap)),
        atr_points=Decimal(str(atr_points)),
        k_atr=Decimal(str(k_atr))
    )

    # Calculate risk budget
    risk_budget = float(request.portfolio_value * request.daily_risk_cap)

    # Calculate risk per share (stop distance)
    unit_risk = float(request.k_atr * request.atr_points)

    # Calculate number of shares
    shares = math.floor(risk_budget / unit_risk)

    return max(0, shares)
```

**Step 3:** Add validation to data ingestion

Update `rapidtrader/data/ingest.py`:
```python
from ..core.models import OHLCVBar

def upsert_bars(symbol: str, bars: pd.DataFrame) -> None:
    """Insert or update daily OHLCV bars in the database.

    Args:
        symbol: Stock ticker symbol
        bars: DataFrame with OHLCV data

    Raises:
        ValidationError: If bar data is invalid
    """
    if bars.empty:
        logger.warning("no_data_to_upsert", symbol=symbol)
        return

    eng = get_engine()

    with eng.begin() as c:
        for d, row in bars.iterrows():
            try:
                # Validate bar data
                validated_bar = OHLCVBar(
                    symbol=symbol,
                    date=d.date() if hasattr(d, 'date') else d,
                    open=Decimal(str(row["Open"])),
                    high=Decimal(str(row["High"])),
                    low=Decimal(str(row["Low"])),
                    close=Decimal(str(row["Close"])),
                    volume=int(row["Volume"])
                )

                c.execute(text("""
                    INSERT INTO bars_daily(symbol, d, open, high, low, close, volume)
                    VALUES (:s, :d, :o, :h, :l, :c, :v)
                    ON CONFLICT (symbol, d) DO UPDATE SET
                        open = :o, high = :h, low = :l, close = :c, volume = :v
                """), {
                    "s": validated_bar.symbol,
                    "d": validated_bar.date,
                    "o": float(validated_bar.open),
                    "h": float(validated_bar.high),
                    "l": float(validated_bar.low),
                    "c": float(validated_bar.close),
                    "v": validated_bar.volume
                })

            except ValidationError as e:
                logger.error("invalid_bar_data", symbol=symbol, date=d, error=str(e))
                continue
            except Exception as e:
                logger.error("upsert_failed", symbol=symbol, date=d, error=str(e))
                continue
```

**Step 4:** Add configuration validation

Update `rapidtrader/core/config.py`:
```python
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, validator, HttpUrl
import os


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)

    # Database
    RT_DB_URL: str = Field(
        "postgresql+psycopg://postgres:postgres@localhost:5432/rapidtrader",
        description="Database connection URL"
    )

    # API Keys
    RT_POLYGON_API_KEY: str = Field(..., min_length=20, description="Polygon.io API key")
    RT_FMP_API_KEY: str = Field("", description="Legacy FMP API key")

    # Alpaca Trading API
    RT_ALPACA_API_KEY: str = Field("", min_length=20)
    RT_ALPACA_SECRET_KEY: str = Field("", min_length=40)
    RT_ALPACA_PAPER: bool = True
    RT_ALPACA_ENDPOINT: HttpUrl = "https://paper-api.alpaca.markets"

    # Market Filter
    RT_MARKET_FILTER_ENABLE: int = Field(1, ge=0, le=1)
    RT_MARKET_FILTER_SMA: int = Field(200, ge=10, le=500, description="SMA period")
    RT_MARKET_FILTER_SYMBOL: str = Field("SPY", regex="^[A-Z]{1,5}$")
    RT_ALLOW_EXITS_IN_BEAR: int = Field(1, ge=0, le=1)
    RT_SELLS_HELD_POSITIONS_ONLY: int = Field(0, ge=0, le=1)

    # Signal Confirmation
    RT_ENABLE_SIGNAL_CONFIRM: int = Field(1, ge=0, le=1)
    RT_CONFIRM_WINDOW: int = Field(3, ge=1, le=10, description="Confirmation window")
    RT_CONFIRM_MIN_COUNT: int = Field(2, ge=1, le=10, description="Min confirmations")

    # ATR Stops
    RT_ENABLE_ATR_STOP: int = Field(1, ge=0, le=1)
    RT_ATR_LOOKBACK: int = Field(14, ge=5, le=50, description="ATR calculation period")
    RT_ATR_STOP_K: float = Field(3.0, gt=0.0, le=10.0, description="ATR multiplier")
    RT_COOLDOWN_DAYS_ON_STOP: int = Field(1, ge=0, le=30)

    # Position Sizing
    RT_START_CAPITAL: float = Field(100_000.0, gt=0.0, description="Starting capital")
    RT_PCT_PER_TRADE: float = Field(0.05, gt=0.0, lt=1.0, description="5% per trade")
    RT_DAILY_RISK_CAP: float = Field(0.005, gt=0.0, lt=0.1, description="0.5% daily risk")
    RT_MAX_EXPOSURE_PER_SECTOR: float = Field(0.30, gt=0.0, le=1.0, description="30% max")

    # Technical Indicators
    RT_USE_POLYGON_INDICATORS: int = Field(0, ge=0, le=1)
    RT_POLYGON_RATE_LIMIT: int = Field(0, ge=0, description="0=unlimited")

    # Logging
    RT_LOG_LEVEL: str = Field("INFO", regex="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$")
    RT_LOG_JSON: bool = False
    RT_LOG_FILE: str = ""

    @validator('RT_DB_URL')
    def validate_db_url_production(cls, v):
        """Prevent using localhost in production."""
        if os.getenv('ENV') == 'production' and 'localhost' in v:
            raise ValueError("Cannot use localhost database in production environment")
        return v

    @validator('RT_CONFIRM_MIN_COUNT')
    def validate_confirmation_count(cls, v, values):
        """Ensure min_count <= window."""
        window = values.get('RT_CONFIRM_WINDOW', 3)
        if v > window:
            raise ValueError(f"RT_CONFIRM_MIN_COUNT ({v}) cannot exceed RT_CONFIRM_WINDOW ({window})")
        return v


settings = Settings()
```

### Validation

Create test to verify validation works:
```python
def test_invalid_config_raises_error():
    """Test that invalid config raises validation error."""
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        Settings(RT_PCT_PER_TRADE=1.5)  # 150% is invalid
```

---

## Summary of Remaining Issues

Due to length constraints, here's the quick reference for remaining high-priority issues:

### **ISSUE #7: Add Error Handling Strategy** (4-6 hours)
- Add custom exception classes
- Wrap external API calls with try/except
- Add circuit breaker pattern for Polygon.io
- Validate pandas operations don't fail on empty data

### **ISSUE #8: Fix N+1 Query Pattern** (6-8 hours)
- Batch load all bars in single query
- Cache sector exposures
- Use JOINs instead of loops

### **ISSUE #9: Add Retry Logic for APIs** (3-4 hours)
- Install `tenacity` library
- Add exponential backoff to Polygon calls
- Add rate limit handling

### **ISSUE #10: Make Jobs Idempotent** (4-6 hours)
- Add unique constraints
- Use `ON CONFLICT` in all inserts
- Add idempotency keys to orders

---

# PHASE 3: MEDIUM PRIORITY (Week 3-4)

Quick reference for medium-priority improvements:

### **ISSUE #11: Add FastAPI REST API** (2-3 weeks)
- Create `api/` module with FastAPI
- Add endpoints for signals, positions, portfolio
- Add WebSocket for real-time updates
- Add OpenAPI documentation

### **ISSUE #12: Add Redis Caching** (1 week)
- Cache market data bars
- Cache calculated indicators
- Add cache invalidation logic

### **ISSUE #13: Add Database Migrations (Alembic)** (1 week)
- Initialize Alembic
- Create migration for current schema
- Add version control for schema changes

### **ISSUE #14: Containerization** (3-5 days)
- Create Dockerfile
- Create docker-compose.yml
- Add development and production configs

### **ISSUE #15: Add CI/CD Pipeline** (2-3 days)
- GitHub Actions for tests
- Auto-deploy to staging
- Code coverage reporting

---

# Timeline Summary

## Minimal Interview-Ready (4 weeks)
- Week 1: Issues #1-#4 (SQL injection, logging, mock data, thread safety)
- Week 2: Issue #5 (Tests - 50% coverage minimum)
- Week 3: Issues #6-#9 (Validation, error handling, performance)
- Week 4: Issue #11 (FastAPI) + polish

## Production-Ready (8 weeks)
- Weeks 1-4: Above
- Week 5: Issues #12-#13 (Redis, Alembic)
- Week 6: Issue #14 (Docker)
- Week 7: Issue #15 + increase test coverage to 80%
- Week 8: Documentation, performance tuning, final polish

---

# Success Metrics

After completing this plan, you should be able to demonstrate:

✅ **Code Quality**
- 70%+ test coverage
- No SQL injection vulnerabilities
- Structured logging throughout
- Proper error handling

✅ **Architecture**
- Clean separation of concerns
- REST API layer
- Caching strategy
- Database migrations

✅ **Production Readiness**
- Thread-safe operations
- Retry logic for external APIs
- Idempotent jobs
- Input validation

✅ **Interview Talking Points**
- "Built a production-grade algorithmic trading system with 75% test coverage"
- "Implemented multi-layer risk management with circuit breakers"
- "Designed RESTful API with FastAPI, achieving 50ms p95 latency"
- "Optimized database queries, reducing job execution time by 80%"

---

**Next Steps:** Start with ISSUE #1 (SQL Injection) - it's the easiest win and takes only 2-4 hours.
