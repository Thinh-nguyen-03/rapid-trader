# RapidTrader Documentation

Complete documentation for the RapidTrader algorithmic trading system.

## Overview

RapidTrader is a fully functional end-of-day (EOD) algorithmic trading system featuring:
- **Trading System**: RSI mean-reversion + SMA crossover strategies with confirmation
- **Risk Management**: Market filter, sector caps, position sizing, stop cooldowns
- **Data Pipeline**: 505 S&P 500 symbols with 125K+ historical bars from Alpaca (free)
- **Job Framework**: Automated EOD workflow (ingest, trade, report)

## Essential Documentation

### Quick Start
- [**SETUP_ENV_GUIDE.md**](../SETUP_ENV_GUIDE.md) - API keys and environment configuration (start here)
- [`environment-setup.md`](environment-setup.md) - Development environment setup
- [`SUPABASE_SETUP.md`](SUPABASE_SETUP.md) - Database setup guide

### System Reference
- [`rapidtrader_mvp_spec.md`](rapidtrader_mvp_spec.md) - Complete system specification
- [`runbook.md`](runbook.md) - Operations guide and daily procedures
- [`technical_trading_primer.md`](technical_trading_primer.md) - Trading concepts overview

### Implementation Guide
- [`MINIMAL_CORE_PACK.md`](MINIMAL_CORE_PACK.md) - Complete implementation reference
- [`signals_and_sizing.md`](signals_and_sizing.md) - Technical indicators and position sizing

## Quick Start Commands

```bash
# 1. Get Alpaca API key (free)
# Sign up at https://alpaca.markets/ for paper trading

# 2. Set up environment
python -m venv .venv && source .venv/bin/activate
pip install -e .

# 3. Configure APIs and database
cp .env.example .env  # Add your Alpaca API keys

# 4. Run the complete trading system
python -m rapidtrader.jobs.eod_ingest --days 300
python -m rapidtrader.jobs.eod_trade --mode dry_run
python -m rapidtrader.jobs.eod_report
```

## Documentation Guide

### For New Users
1. **Get API Keys**: Follow [SETUP_ENV_GUIDE.md](../SETUP_ENV_GUIDE.md) to get Alpaca credentials
2. **Setup Environment**: Complete [environment-setup.md](environment-setup.md)
3. **Configure Database**: Set up using [SUPABASE_SETUP.md](SUPABASE_SETUP.md)
4. **Understand System**: Read [rapidtrader_mvp_spec.md](rapidtrader_mvp_spec.md)
5. **Daily Operations**: Reference [runbook.md](runbook.md)

### For Developers
- **System Architecture**: [`rapidtrader_mvp_spec.md`](rapidtrader_mvp_spec.md)
- **Implementation Details**: [`MINIMAL_CORE_PACK.md`](MINIMAL_CORE_PACK.md)
- **Signals & Sizing**: [`signals_and_sizing.md`](signals_and_sizing.md)
- **Development Setup**: [`environment-setup.md`](environment-setup.md)

### For Operators
- **Daily Procedures**: [`runbook.md`](runbook.md)
- **Troubleshooting**: See runbook emergency procedures section
- **Monitoring**: Review runbook metrics and alert thresholds

## System Components

### Trading Strategies
- **RSI Mean-Reversion**: Oversold entry (RSI<30), momentum exit (RSI>55)
- **SMA Crossover**: 20/100 SMA with confirmation logic
- **Signal Confirmation**: 2-of-3 strategy agreement required

### Risk Management
- **Market Filter**: SPY 200-SMA bull/bear regime detection
- **Sector Limits**: Maximum 30% exposure per sector
- **Position Sizing**: Fixed-fractional (5%) with ATR targeting
- **Stop Losses**: ATR-based stops with cooldown periods
- **Kill Switch**: -12% drawdown emergency stop

### Data Infrastructure
- **Market Data**: Alpaca Markets API (free paper trading account)
- **Company Fundamentals**: Financial Modeling Prep API (optional, 250 free req/day)
- **Market Calendar**: pandas_market_calendars (open source)
- **Database**: PostgreSQL / Supabase

### Job Framework
- **EOD Ingest**: Daily data collection from Alpaca
- **EOD Trade**: Signal generation and order creation
- **EOD Report**: Performance and risk reporting

## Additional Resources

- **Main README**: [../README.md](../README.md) - Project overview
- **Getting Started**: [../START_HERE.md](../START_HERE.md) - Quick start guide
- **Setup Guide**: [../SETUP_ENV_GUIDE.md](../SETUP_ENV_GUIDE.md) - Complete environment setup

## Support

For issues or questions:
1. Check the relevant documentation above
2. Review [runbook.md](runbook.md) troubleshooting section
3. Verify API connectivity with `python test_alpaca_migration.py`
4. Check database connection with `python tools/testing/test_database_connection.py`
