# RapidTrader Documentation

Complete documentation for the RapidTrader algorithmic trading system.

## 🎯 System Status: **100% Complete & Operational**

RapidTrader is a fully functional end-of-day (EOD) algorithmic trading system featuring:
- ✅ **Complete Trading System**: RSI mean-reversion + SMA crossover strategies
- ✅ **Risk Management**: Market filter, sector caps, position sizing, stop cooldowns
- ✅ **Data Pipeline**: 505 S&P 500 symbols with 125K+ historical bars via Polygon.io
- ✅ **Job Framework**: Automated EOD workflow (ingest → trade → report)
- ✅ **Production Ready**: All components tested and validated

## 📚 Essential Documentation

### Quick Start
- [`environment-setup.md`](environment-setup.md) - Development environment setup
- [`POLYGON_SETUP.md`](POLYGON_SETUP.md) - Polygon.io API configuration
- [`SUPABASE_SETUP.md`](SUPABASE_SETUP.md) - Database setup guide

### System Reference
- [`rapidtrader_mvp_spec.md`](rapidtrader_mvp_spec.md) - Complete system specification
- [`runbook.md`](runbook.md) - Operations guide and daily procedures
- [`technical_trading_primer.md`](technical_trading_primer.md) - Trading concepts overview

### Implementation Guide
- [`MINIMAL_CORE_PACK.md`](MINIMAL_CORE_PACK.md) - Complete implementation reference

## 🚀 Quick Start Commands

```bash
# 1. Set up environment (see environment-setup.md)
python -m venv .venv && source .venv/bin/activate
pip install -e .

# 2. Configure APIs and database (see setup guides)
cp .env.example .env  # Add your API keys

# 3. Run the complete trading system
python -m rapidtrader.jobs.eod_ingest --days 300
python -m rapidtrader.jobs.eod_trade --mode dry_run
python -m rapidtrader.jobs.eod_report
```

## 📖 Documentation Guide

- **New Users**: Start with `environment-setup.md` → `POLYGON_SETUP.md` → `SUPABASE_SETUP.md`
- **System Overview**: Read `rapidtrader_mvp_spec.md` for complete architecture
- **Daily Operations**: Use `runbook.md` for operational procedures
- **Customization**: Reference `MINIMAL_CORE_PACK.md` for implementation details