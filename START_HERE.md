# 🚀 RapidTrader - START HERE

Welcome to RapidTrader! This guide will get you up and running quickly.

## 🎯 What is RapidTrader?

RapidTrader is an **End-of-Day (EOD) algorithmic trading system** designed for systematic equity trading. It focuses on:

- **S&P 500 stocks** using technical analysis strategies
- **Risk management** with portfolio-level controls
- **Clean, maintainable code** with minimal dependencies
- **Cost-effective operation** using free and low-cost data sources

## ⚡ Quick Start (5 minutes)

### 1. Get Your Free API Key
- Go to: https://financialmodelingprep.com/developer/docs
- Sign up for free account (250 API calls/day)
- Copy your API key

### 2. Setup Environment
```bash
# Clone and install
git clone <repository-url>
cd rapidtrader-starter-v4.1
pip install -e .

# Configure API key
echo "RT_FMP_API_KEY=your_key_here" > .env
```

### 3. Test & Run
```bash
# Test API connection
python scripts/test_fmp_api.py

# Seed S&P 500 symbols
python scripts/seed_sp500.py
```

**That's it!** You now have 500+ S&P 500 symbols ready for trading strategies.

## 📚 What's Next?

### If You Want to Understand the System
- 📖 **Read**: [docs/rapidtrader_mvp_spec.md](docs/rapidtrader_mvp_spec.md) - Complete technical specification
- 🏗️ **Architecture**: [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) - How the code is organized
- 📈 **Trading Concepts**: [docs/technical_trading_primer.md](docs/technical_trading_primer.md) - Technical analysis primer

### If You Want to Start Implementing
- ✅ **Checklist**: [docs/LEARNING_PATH/Apply_It_Now.md](docs/LEARNING_PATH/Apply_It_Now.md) - Step-by-step implementation
- 📋 **Tasks**: [TASKS.md](TASKS.md) - Detailed task breakdown
- 📊 **Progress**: [PROGRESS.md](PROGRESS.md) - Current system status

### If You Want to Setup Infrastructure
- 🗄️ **Database**: [docs/SUPABASE_SETUP.md](docs/SUPABASE_SETUP.md) - Database configuration
- 🔧 **Environment**: [docs/environment-setup.md](docs/environment-setup.md) - Development setup
- 🔌 **API**: [docs/FMP_SETUP.md](docs/FMP_SETUP.md) - Financial Modeling Prep setup

### If You Want to Operate the System
- 📋 **Operations**: [docs/runbook.md](docs/runbook.md) - Day-to-day operations guide
- 🚀 **Enhancements**: [docs/mvp_enhancements_addendum.md](docs/mvp_enhancements_addendum.md) - Future improvements

## 🎯 Current System Status

### ✅ **What's Working Now**
- **Database schema** - All tables created and ready
- **S&P 500 data** - Real-time symbol and sector fetching
- **Technical indicators** - SMA, RSI, ATR calculations
- **Data ingestion** - yfinance integration for OHLCV data
- **Configuration** - All trading parameters configurable

### 🚧 **What's Next to Implement**
- **Trading strategies** - RSI mean-reversion and SMA crossover
- **Risk management** - Position sizing and sector limits
- **Job framework** - Automated EOD workflow
- **Reporting** - Daily performance analytics

**Progress: ~40% complete** - Foundation is solid, ready for core trading logic.

## 🛠️ Development Workflow

### For New Contributors
1. **Start Here** → [docs/environment-setup.md](docs/environment-setup.md)
2. **Understand Architecture** → [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md)
3. **Pick a Task** → [TASKS.md](TASKS.md)
4. **Follow Checklist** → [docs/LEARNING_PATH/Apply_It_Now.md](docs/LEARNING_PATH/Apply_It_Now.md)

### For System Operators
1. **Setup Guide** → [docs/FMP_SETUP.md](docs/FMP_SETUP.md) + [docs/SUPABASE_SETUP.md](docs/SUPABASE_SETUP.md)
2. **Daily Operations** → [docs/runbook.md](docs/runbook.md)
3. **Monitor Progress** → [PROGRESS.md](PROGRESS.md)

## 🔧 System Architecture Overview

```
Data Sources     RapidTrader Core        Database
┌─────────────┐  ┌─────────────────┐    ┌─────────────┐
│ FMP API     │──│ • Indicators    │────│ PostgreSQL  │
│ yfinance    │  │ • Strategies    │    │ / Supabase  │
│ Yahoo Finance│  │ • Risk Mgmt     │    │             │
└─────────────┘  │ • Jobs          │    └─────────────┘
                 └─────────────────┘
                         │
                 ┌─────────────────┐
                 │ Outputs         │
                 │ • Orders        │
                 │ • Reports       │
                 │ • Alerts        │
                 └─────────────────┘
```

## 💡 Key Design Principles

### Simple & Focused
- **EOD-only**: No real-time complexity
- **S&P 500 only**: Liquid, well-known stocks
- **Minimal dependencies**: Easy to understand and maintain

### Cost-Effective
- **Free data sources**: yfinance for OHLCV data
- **Cheap APIs**: FMP free tier for S&P 500 data
- **Efficient processing**: Bulk operations, minimal API calls

### Production-Ready
- **Database persistence**: All data and decisions stored
- **Risk management**: Portfolio-level controls and limits
- **Error handling**: Graceful failures and recovery
- **Monitoring**: Comprehensive logging and reporting

## 📞 Getting Help

### Documentation Order (Start → Advanced)
1. **START_HERE.md** ← You are here
2. **[docs/FMP_SETUP.md](docs/FMP_SETUP.md)** - API setup
3. **[TASKS.md](TASKS.md)** - What to implement
4. **[docs/rapidtrader_mvp_spec.md](docs/rapidtrader_mvp_spec.md)** - Complete specification
5. **[docs/runbook.md](docs/runbook.md)** - Operations guide

### Common Questions
- **"How do I get started?"** → Follow the Quick Start above
- **"What should I implement first?"** → Check [TASKS.md](TASKS.md) critical path
- **"How does the system work?"** → Read [docs/rapidtrader_mvp_spec.md](docs/rapidtrader_mvp_spec.md)
- **"What's the current status?"** → Check [PROGRESS.md](PROGRESS.md)

### File Organization
- **Root files**: Project overview and management
- **docs/**: All documentation and guides
- **rapidtrader/**: Main source code
- **scripts/**: Utility scripts and tools

---

**Ready to build a trading system?** Pick your path above and let's get started! 🚀
