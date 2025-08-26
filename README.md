# RapidTrader

Minimal EOD (End-of-Day) algorithmic trading system for Python.

## Quick Start

1. **Get FMP API Key** (free): https://financialmodelingprep.com/developer/docs

2. **Setup**:
   ```bash
   pip install -e .
   echo "RT_FMP_API_KEY=your_key_here" > .env
   ```

3. **Run**:
   ```bash
   # Test FMP connection
   python scripts/test_fmp_api.py
   
   # Seed S&P 500 symbols
   python scripts/seed_sp500.py
   ```

## What's Included

- **S&P 500 data**: Automatic symbol and sector fetching via FMP API
- **OHLCV data**: yfinance integration for price/volume data  
- **Technical indicators**: SMA, RSI, ATR implementations
- **Database**: PostgreSQL/Supabase ready schema
- **Minimal codebase**: Clean, focused implementation

## Core Components

- `rapidtrader/core/` - Configuration and database
- `rapidtrader/data/` - Data fetching (FMP + yfinance)
- `rapidtrader/indicators/` - Technical analysis functions
- `scripts/` - Setup and utility scripts
- `docs/` - Essential documentation only

## Database Setup

```sql
-- Run scripts/setup_db.sql in your PostgreSQL database
CREATE TABLE symbols (symbol TEXT PRIMARY KEY, sector TEXT, is_active BOOLEAN);
CREATE TABLE bars_daily (symbol TEXT, d DATE, open REAL, high REAL, low REAL, close REAL, volume INTEGER);
-- See scripts/setup_db.sql for complete schema
```

## Configuration

Environment variables in `.env`:
- `RT_FMP_API_KEY` - Financial Modeling Prep API key
- `RT_DB_URL` - Database connection string
- See `rapidtrader/core/config.py` for all options

## Architecture

**EOD-focused**: Designed for end-of-day trading strategies, not high-frequency.

**Simple & Clean**: Minimal dependencies, straightforward data flow.

**Production-ready**: Database persistence, error handling, configurable parameters.
