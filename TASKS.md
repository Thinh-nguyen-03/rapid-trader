# RapidTrader MVP Implementation Tasks

_Based on MINIMAL_CORE_PACK.md - A complete roadmap from current state to working EOD trading system_

## 🎯 Goal
Implement a complete EOD (End-of-Day) algorithmic trading system with:
- RSI Mean-Reversion + SMA Crossover strategies
- SPY 200-SMA market filter with 2-of-3 confirmation
- ATR-based position sizing and stops
- Sector exposure caps and stop cooldown
- PostgreSQL persistence with dry-run order generation

---

## 📋 Implementation Phases

### Phase 1: Database & Infrastructure ✅ COMPLETE
- [x] **1.1** Update `scripts/setup_db.sql` with 5 new tables
  - [x] `signals_daily` - Strategy signals with strength
  - [x] `orders_eod` - Dry-run order records  
  - [x] `positions` - Position tracking with sectors
  - [x] `market_state` - SPY SMA200 cache + filtering metrics
  - [x] `symbol_events` - Stop cooldown tracking
- [x] **1.2** Create `rapidtrader/core/db.py` with `get_engine()` function
- [x] **1.3** Update `rapidtrader/core/config.py` with all RT_ parameters
- [x] **1.4** Add missing table to setup: `bars_daily` (OHLCV data)
- [x] **1.5** Set up Supabase cloud database with verified connectivity

### Phase 2: Core Indicators 🔧 MOSTLY COMPLETE  
- [x] **2.1** Create `rapidtrader/indicators/` module
- [x] **2.2** Implement `rapidtrader/indicators/core.py`:
  - [x] `sma(series, n)` - Simple Moving Average
  - [x] `rsi_wilder(close, window=14)` - RSI with Wilder's smoothing
  - [x] `atr(high, low, close, n=14)` - Average True Range
- [x] **2.3** Add `__init__.py` files for proper imports
- [x] **2.4** Basic testing with synthetic data
- [ ] **2.5** Unit tests for indicator accuracy and edge cases
- [ ] **2.6** Performance validation with real market data

### Phase 3: Strategy Implementation 📈 HIGH PRIORITY
- [ ] **3.1** Create `rapidtrader/strategies/` module 
- [ ] **3.2** Implement confirmation logic:
  - [ ] `rapidtrader/strategies/confirmation.py` - 2-of-3 signal accumulator
- [ ] **3.3** Implement strategies:
  - [ ] `rapidtrader/strategies/rsi_mr.py` - RSI Mean-Reversion
  - [ ] `rapidtrader/strategies/sma_cross.py` - SMA Crossover
- [ ] **3.4** Add strategy unit tests (optional but recommended)

### Phase 4: Risk Management 🛡️ HIGH PRIORITY
- [ ] **4.1** Create `rapidtrader/risk/` module
- [ ] **4.2** Implement position sizing:
  - [ ] `rapidtrader/risk/sizing.py` - Fixed-fractional & ATR-target sizing
- [ ] **4.3** Implement risk controls:
  - [ ] `rapidtrader/risk/controls.py` - Market filter, sector caps, SPY cache
- [ ] **4.4** Implement stop management:
  - [ ] `rapidtrader/risk/stop_cooldown.py` - Stop hit tracking & cooldown

### Phase 5: Data Pipeline 📊 HIGH PRIORITY (NEXT)
- [x] **5.1** Create `rapidtrader/data/` module
- [x] **5.2** Implement data ingestion:
  - [x] `rapidtrader/data/ingest.py` - yfinance → Supabase pipeline
- [x] **5.3** Implement S&P 500 symbol management:
  - [x] `rapidtrader/data/sp500_api.py` - FMP API integration
- [x] **5.4** Create symbol seeding script for S&P 500 universe

### Phase 6: Job Framework 🔄 HIGH PRIORITY
- [ ] **6.1** Create `rapidtrader/jobs/` module
- [ ] **6.2** Implement core jobs:
  - [ ] `rapidtrader/jobs/eod_ingest.py` - Daily data ingestion
  - [ ] `rapidtrader/jobs/eod_trade.py` - Signal generation & order creation
  - [ ] `rapidtrader/jobs/eod_report.py` - Daily summary report
- [ ] **6.3** Make jobs executable as modules (`python -m rapidtrader.jobs.X`)

### Phase 7: Symbol Management 📝 MEDIUM PRIORITY
- [x] **7.1** Create `scripts/seed_sp500.py` - Populate symbols table
- [x] **7.2** Add sector information to symbols (for sector caps)
- [ ] **7.3** Symbol maintenance utilities

### Phase 8: System Integration 🔗 MEDIUM PRIORITY  
- [ ] **8.1** Update `scripts/bootstrap.sh` with full setup sequence
- [ ] **8.2** Create `.env.example` with all configuration options
- [ ] **8.3** Update `pyproject.toml` dependencies if needed
- [ ] **8.4** End-to-end smoke test workflow

### Phase 9: Operational Features ⚙️ LOW PRIORITY
- [x] **9.1** Logging framework (minimal, per user preference) - Clean logging without emojis/symbols implemented
- [ ] **9.2** Error handling & graceful degradation
- [ ] **9.3** Performance monitoring hooks
- [ ] **9.4** Kill switch implementation (if 20-day Sharpe < -1.0)

### Phase 10: Future Enhancements 🚀 FUTURE
- [ ] **10.1** Alpaca API integration for paper trading
- [ ] **10.2** Backtesting framework with cost sensitivity
- [ ] **10.3** Portfolio analytics & Sharpe ratio calculation  
- [ ] **10.4** Advanced order types (limit, stop-limit)
- [ ] **10.5** Real-time monitoring dashboard

---

## 🔥 Critical Path (Minimum Viable Implementation)

**Priority Order for Working System:**
1. **Database setup** (Phase 1) - Foundation
2. **Core indicators** (Phase 2) - Technical analysis
3. **Data pipeline** (Phase 5) - Market data ingestion
4. **Strategies** (Phase 3) - Signal generation  
5. **Risk management** (Phase 4) - Position sizing & controls
6. **Jobs framework** (Phase 6) - EOD workflow automation

**After these 6 phases:** You'll have a complete working EOD trading system.

## 🎉 **Foundation Milestones Achieved**

### ✅ **Database Setup Complete**
- **Supabase Project**: `rapidtrader-mvp` (lxwaqpzhxpxzeygnegnv)
- **Region**: us-east-1  
- **Status**: ACTIVE_HEALTHY
- **Connection**: Verified working with all tables
- **Sample Data**: 6 symbols added (SPY, AAPL, MSFT, GOOGL, TSLA, NVDA)

### ✅ **Technical Foundation Complete**
- **Configuration**: All RT_ parameters working
- **Indicators**: SMA, RSI, ATR tested and functional
- **Project Structure**: Clean, scalable organization
- **Dependencies**: All packages installed and verified

### ✅ **Data Pipeline Foundation Complete**
- **FMP Integration**: S&P 500 symbol fetching implemented
- **yfinance Integration**: OHLCV data ingestion ready
- **Symbol Seeding**: Automated S&P 500 population
- **API Testing**: Connectivity verification tools

---

## 📐 Implementation Standards

- **Code Organization**: Follow user preference for 1-3 files per module [[memory:6863722]]
- **Logging**: Minimal logging, critical/error only, no emojis [[memory:6863719]]
- **Testing**: Unit tests for indicators and strategies (optional)
- **Documentation**: Inline docstrings for public functions
- **Error Handling**: Graceful failures with meaningful error messages

---

## 🧪 Success Criteria

**System is complete when:**
- [ ] All database tables exist and are populated
- [ ] `python scripts/seed_sp500.py` successfully populates 500+ symbols
- [ ] `python -m rapidtrader.jobs.eod_ingest` successfully downloads data
- [ ] `python -m rapidtrader.jobs.eod_trade` generates signals and orders
- [ ] `python -m rapidtrader.jobs.eod_report` shows filtering metrics
- [ ] Market state shows SPY bull/bear regime
- [ ] Orders table has buy/sell records
- [ ] System respects sector caps and stop cooldowns

**Acceptance Test Command:**
```bash
# Full end-to-end test
python scripts/seed_sp500.py                              # Populate symbols
python -m rapidtrader.jobs.eod_ingest --days 300         # Download data
python -m rapidtrader.jobs.eod_trade --mode dry_run      # Generate signals
python -m rapidtrader.jobs.eod_report                    # Create report
```

---

## 📞 Next Actions

**Immediate Priority (Phase 3 & 4):**
1. **Implement trading strategies** - RSI mean-reversion and SMA crossover
2. **Implement risk management** - Position sizing and market filters
3. **Test strategy logic** - Verify signal generation with real data
4. **Validate risk controls** - Ensure proper constraint enforcement

**Following Priority (Phase 6):**
1. **Build job framework** - EOD automation pipeline
2. **End-to-end testing** - Complete workflow validation
3. **Performance optimization** - Ensure acceptable execution times
4. **Documentation updates** - Keep documentation current

**System Status:** Ready to implement core trading logic and risk management systems.
