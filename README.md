# RapidTrader

**End-of-Day Algorithmic Trading System**

**Status**: Complete and operational

## Overview

RapidTrader is a production-ready algorithmic trading system featuring:

- **Trading Strategies**: RSI mean-reversion and SMA crossover with 2-of-3 confirmation
- **Risk Management**: Market filter, sector caps (30%), position sizing, stop cooldowns
- **Data Pipeline**: 505 S&P 500 symbols with Alpaca Markets data
- **Job Framework**: Complete EOD automation (ingest, trade, report)
- **Database**: PostgreSQL/Supabase integration with 7 tables

## Quick Start

1. **Get Free Alpaca API Key**: https://alpaca.markets/ (Paper trading account - 100% free)

2. **Setup Environment**:
   ```bash
   git clone <your-repo>
   cd rapid-trader
   python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
   pip install -e .

   # Configure API keys (see SETUP_ENV_GUIDE.md)
   cp .env.example .env  # Add your Alpaca API keys
   ```

3. **Run Complete Trading System**:
   ```bash
   # Daily data ingestion
   python -m rapidtrader.jobs.eod_ingest --days 300

   # Generate signals and create orders
   python -m rapidtrader.jobs.eod_trade --mode dry_run

   # Generate daily report
   python -m rapidtrader.jobs.eod_report
   ```

## System Components

- **Strategies**: RSI mean-reversion + SMA crossover with confirmation logic
- **Risk Controls**: SPY 200-SMA market filter, sector exposure limits
- **Position Sizing**: Fixed-fractional + ATR-target sizing algorithms
- **Data Quality**: 125K+ historical bars with real-time updates
- **Automation**: Complete EOD workflow with job scheduling

## Documentation

- **Getting Started**: See [docs/README.md](docs/README.md) for complete documentation
- **Setup Guide**: [SETUP_ENV_GUIDE.md](SETUP_ENV_GUIDE.md) - Environment and API setup
- **Operations**: [docs/runbook.md](docs/runbook.md) for daily operational procedures
- **System Architecture**: [docs/rapidtrader_mvp_spec.md](docs/rapidtrader_mvp_spec.md)

## Key Features

- Production-ready trading system with all components implemented
- Comprehensive risk controls and position sizing
- Free institutional-quality market data via Alpaca
- Full EOD workflow with job scheduling
- All indicators tested with real market data
- Complete operational and technical documentation

## Trading System

### Strategies
- **RSI Mean-Reversion**: Buy oversold (RSI<30), sell at 55+ with 2-of-3 confirmation
- **SMA Crossover**: 20/100 SMA crossover with 2-day confirmation
- **Signal Confirmation**: Reduces false signals with confirmation logic

### Risk Management
- **Market Filter**: SPY 200-SMA bull/bear detection (blocks entries in bear markets)
- **Sector Caps**: Maximum 30% exposure per sector
- **Position Sizing**: Fixed-fractional (5%) + ATR-target sizing
- **Stop Management**: ATR-based stops with 1-day cooldown periods

### Data and Infrastructure
- **505 S&P 500 Symbols**: Complete universe with sector classification
- **125K+ Historical Bars**: 1+ years of high-quality OHLCV data
- **7-Table Database**: Comprehensive data model for signals, orders, positions
- **Job Automation**: Daily data ingestion, signal generation, reporting

## System Architecture

- **EOD-Focused**: Designed for end-of-day systematic trading strategies
- **Production-Ready**: Database persistence, error handling, comprehensive risk management
- **Modular Design**: Clean separation between data, strategies, risk, and execution
- **Free Market Data**: Alpaca integration for institutional-quality data (no cost)

## Requirements

- Python 3.11+
- PostgreSQL or Supabase account
- Alpaca API key (free paper trading account)
- Optional: Financial Modeling Prep API key for sector data (free 250 req/day)

---

See [docs/README.md](docs/README.md) for complete documentation.
