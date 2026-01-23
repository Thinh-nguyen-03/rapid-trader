# RapidTrader - Getting Started

**End-of-Day Algorithmic Trading System**

**Status**: Complete and ready for production trading

## Overview

RapidTrader is a production-ready EOD algorithmic trading system featuring:

- **Trading Strategies**: RSI mean-reversion + SMA crossover with confirmation
- **Risk Management**: Market filter, sector caps, position sizing, stop cooldowns
- **Data Pipeline**: 505 S&P 500 symbols with 125K+ bars via Alpaca Markets (free)
- **Automation**: Complete EOD workflow (ingest, trade, report)

## Quick Start

### 1. Get Your Free Alpaca API Key
- Go to: https://alpaca.markets/
- Sign up for free paper trading account (no credit card required)
- Navigate to "Your API Keys" in dashboard
- Generate and copy both API Key and Secret Key

### 2. Setup Environment
```bash
# Clone and setup
git clone <repository-url>
cd rapid-trader
python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e .

# Configure environment (see SETUP_ENV_GUIDE.md for details)
cp .env.example .env  # Add your Alpaca API keys
```

### 3. Run Complete Trading System
```bash
# Daily data ingestion (loads all S&P 500 data)
python -m rapidtrader.jobs.eod_ingest --days 300

# Generate trading signals and create orders
python -m rapidtrader.jobs.eod_trade --mode dry_run

# Generate daily performance report
python -m rapidtrader.jobs.eod_report
```

### 4. Verify System Health (Optional)
```bash
# Test core components
python tools/testing/test_database_connection.py
python tools/testing/test_indicator_accuracy.py

# Check S&P 500 symbols (should show 505 symbols)
python scripts/seed_sp500.py
```

After completing these steps, you will have:
- Real market data from 505 S&P 500 symbols
- Trading signals generated with RSI + SMA strategies
- Risk management and position sizing
- Daily performance reports

## Documentation

### Understanding the System
- **System Overview**: [docs/rapidtrader_mvp_spec.md](docs/rapidtrader_mvp_spec.md) - Complete technical specification
- **Trading Concepts**: [docs/technical_trading_primer.md](docs/technical_trading_primer.md) - Technical analysis primer
- **Documentation Hub**: [docs/README.md](docs/README.md) - All documentation organized

### Setup and Configuration
- **Environment Setup**: [SETUP_ENV_GUIDE.md](SETUP_ENV_GUIDE.md) - API keys and environment configuration
- **Database Setup**: [docs/SUPABASE_SETUP.md](docs/SUPABASE_SETUP.md) - Database configuration
- **Development Environment**: [docs/environment-setup.md](docs/environment-setup.md) - Development tools

### Operating the System
- **Daily Operations**: [docs/runbook.md](docs/runbook.md) - Day-to-day operational procedures

## Implementation Status

**Fully Implemented Features**:
- Complete trading system with RSI mean-reversion + SMA crossover strategies
- Risk management: market filter, sector caps, position sizing, stop cooldowns
- Data pipeline: 505 S&P 500 symbols with 125K+ historical bars from Alpaca
- Job framework: complete EOD automation (ingest, trade, report)
- Database: all 7 tables operational with comprehensive data model

## Usage Workflow

### For New Users
1. **Environment Setup**: [SETUP_ENV_GUIDE.md](SETUP_ENV_GUIDE.md) - Get Alpaca API keys
2. **Database Configuration**: [docs/SUPABASE_SETUP.md](docs/SUPABASE_SETUP.md) - Setup database
3. **Run the System**: Follow Quick Start above
4. **Daily Operations**: [docs/runbook.md](docs/runbook.md)

### For System Customization
1. **Study Architecture**: [docs/rapidtrader_mvp_spec.md](docs/rapidtrader_mvp_spec.md)
2. **Understand Implementation**: [docs/MINIMAL_CORE_PACK.md](docs/MINIMAL_CORE_PACK.md)
3. **Modify Strategies**: See `rapidtrader/strategies/` modules
4. **Adjust Risk Controls**: See `rapidtrader/risk/` modules

## System Architecture

```
Data Sources     RapidTrader Core        Database
+-----------+    +---------------+       +-----------+
| Alpaca    |----| - Indicators  |-------| PostgreSQL|
| (FREE)    |    | - Strategies  |       | / Supabase|
| FMP (opt) |    | - Risk Mgmt   |       |           |
+-----------+    | - Jobs        |       +-----------+
                 +---------------+
                        |
                 +---------------+
                 | Outputs       |
                 | - Orders      |
                 | - Reports     |
                 | - Alerts      |
                 +---------------+
```

## Design Principles

### Simple and Focused
- **EOD-only**: No real-time complexity
- **S&P 500 only**: Liquid, well-known stocks
- **Minimal dependencies**: Easy to understand and maintain

### Free Professional Data
- **Zero-cost data source**: Alpaca provides institutional-quality market data for free
- **Complete coverage**: 505 S&P 500 symbols with 125K+ historical bars
- **Real-time updates**: Daily data ingestion keeps system current

### Production-Ready
- **Complete implementation**: All trading, risk, and operational components
- **Comprehensive testing**: All indicators validated with real market data
- **Database persistence**: Full audit trail of all signals and orders
- **Risk management**: Multi-layer risk controls and position limits

## Getting Help

### Documentation Navigation
1. **START_HERE.md** - You are here
2. **[SETUP_ENV_GUIDE.md](SETUP_ENV_GUIDE.md)** - Environment and API setup
3. **[docs/README.md](docs/README.md)** - Documentation hub
4. **[docs/rapidtrader_mvp_spec.md](docs/rapidtrader_mvp_spec.md)** - Complete specification
5. **[docs/runbook.md](docs/runbook.md)** - Operations guide

### Common Questions
- **"How do I get started?"** - Follow the Quick Start above
- **"How does the system work?"** - Read [docs/rapidtrader_mvp_spec.md](docs/rapidtrader_mvp_spec.md)
- **"How do I operate it daily?"** - Check [docs/runbook.md](docs/runbook.md)
- **"Can I customize strategies?"** - See `rapidtrader/strategies/` modules

### System Organization
- **docs/**: All user documentation and guides
- **rapidtrader/**: Complete trading system source code
- **scripts/**: Setup and utility scripts
- **tools/**: Testing and validation utilities

## Cost Savings

RapidTrader now uses **100% free market data** from Alpaca:
- **Alpaca Paper Trading**: Free historical and real-time data
- **Optional FMP**: Free 250 requests/day for sector data
- **Total Monthly Cost**: $0 (previously $199/month)
