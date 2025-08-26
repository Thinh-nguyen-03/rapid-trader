# Apply It Now - Implementation Checklist

Quick reference for implementing RapidTrader features step by step.

## Phase 1: Foundation Setup ✅

### Database & Configuration
- [ ] Set up Supabase or PostgreSQL database
- [ ] Run `scripts/setup_db.sql` to create tables
- [ ] Configure `.env` file with database URL
- [ ] Test database connection

### S&P 500 Data
- [ ] Get FMP API key (free tier)
- [ ] Add `RT_FMP_API_KEY` to `.env`
- [ ] Run `python scripts/seed_sp500.py`
- [ ] Verify 500+ symbols in database

### Basic Data Pipeline
- [ ] Test yfinance connection
- [ ] Download sample data for 5-10 symbols
- [ ] Verify OHLCV data in `bars_daily` table

## Phase 2: Technical Indicators ✅

### Core Indicators
- [ ] Test SMA calculation with `rapidtrader.indicators.core.sma()`
- [ ] Test RSI calculation with `rapidtrader.indicators.core.rsi_wilder()`
- [ ] Test ATR calculation with `rapidtrader.indicators.core.atr()`
- [ ] Verify indicators work with real market data

### Data Quality
- [ ] Check for missing data gaps
- [ ] Validate indicator calculations against known values
- [ ] Test with different time periods

## Phase 3: Strategy Implementation 🚧

### RSI Mean Reversion Strategy
- [ ] Create `rapidtrader/strategies/rsi_mr.py`
- [ ] Implement RSI oversold/overbought logic (RSI < 30 = buy signal)
- [ ] Add 2-of-3 confirmation window
- [ ] Test with historical data

### SMA Crossover Strategy  
- [ ] Create `rapidtrader/strategies/sma_cross.py`
- [ ] Implement SMA20/SMA50 crossover logic
- [ ] Add signal strength calculation
- [ ] Test with different SMA periods

### Signal Confirmation
- [ ] Create `rapidtrader/strategies/confirmation.py`
- [ ] Implement 2-of-3 signal accumulator
- [ ] Combine RSI and SMA signals
- [ ] Test signal filtering logic

## Phase 4: Risk Management 🚧

### Position Sizing
- [ ] Create `rapidtrader/risk/sizing.py`
- [ ] Implement fixed-fractional sizing (5% per trade)
- [ ] Implement ATR-based target sizing
- [ ] Test with different risk levels

### Market Filter
- [ ] Create `rapidtrader/core/market_state.py`
- [ ] Implement SPY 200-SMA market filter
- [ ] Cache SPY data for performance
- [ ] Test bull/bear market detection

### Risk Controls
- [ ] Create `rapidtrader/risk/controls.py`
- [ ] Implement sector exposure caps (30% max per sector)
- [ ] Add daily risk limits
- [ ] Test risk constraint enforcement

### Stop Loss Management
- [ ] Create `rapidtrader/risk/stop_cooldown.py`
- [ ] Implement ATR-based stops (3x ATR)
- [ ] Add stop cooldown period (1 day)
- [ ] Track stop events in database

## Phase 5: Data Pipeline 🚧

### EOD Data Ingestion
- [ ] Create `rapidtrader/jobs/eod_ingest.py`
- [ ] Automate daily data download
- [ ] Handle data quality issues
- [ ] Log ingestion results

### Market State Updates
- [ ] Automate SPY SMA200 calculation
- [ ] Update market state daily
- [ ] Track regime changes
- [ ] Alert on market shifts

### Symbol Maintenance
- [ ] Periodic S&P 500 updates
- [ ] Handle index changes
- [ ] Maintain sector classifications
- [ ] Archive delisted symbols

## Phase 6: Job Framework 🚧

### EOD Trading Job
- [ ] Create `rapidtrader/jobs/eod_trade.py`
- [ ] Generate signals for all symbols
- [ ] Apply risk filters
- [ ] Create dry-run orders
- [ ] Log trading decisions

### Reporting Job
- [ ] Create `rapidtrader/jobs/eod_report.py`
- [ ] Generate daily performance summary
- [ ] Track portfolio metrics
- [ ] Alert on notable events
- [ ] Export results

### Job Scheduling
- [ ] Set up cron jobs for automation
- [ ] Handle job dependencies
- [ ] Error notification system
- [ ] Job monitoring dashboard

## Phase 7: Testing & Validation 🧪

### Unit Tests
- [ ] Test all indicator calculations
- [ ] Test strategy signal generation
- [ ] Test risk management logic
- [ ] Test database operations

### Integration Tests
- [ ] Test complete data pipeline
- [ ] Test end-to-end trading workflow
- [ ] Test error handling
- [ ] Test with edge cases

### Backtesting
- [ ] Implement simple backtesting framework
- [ ] Test strategies on historical data
- [ ] Calculate performance metrics
- [ ] Optimize parameters

## Phase 8: Production Readiness 🚀

### Monitoring
- [ ] Set up logging framework
- [ ] Monitor API usage and limits
- [ ] Track system performance
- [ ] Alert on failures

### Error Handling
- [ ] Graceful degradation on API failures
- [ ] Retry logic for transient errors
- [ ] Fallback data sources
- [ ] Error notification system

### Documentation
- [ ] API documentation
- [ ] Deployment guide
- [ ] Troubleshooting guide
- [ ] User manual

### Security
- [ ] Secure API key management
- [ ] Database security review
- [ ] Access control implementation
- [ ] Audit logging

## Quick Commands Reference

```bash
# Development
python scripts/test_fmp_api.py          # Test API connection
python scripts/seed_sp500.py            # Update S&P 500 symbols

# Future commands (when implemented)
python -m rapidtrader.jobs.eod_ingest   # Download daily data
python -m rapidtrader.jobs.eod_trade    # Generate signals
python -m rapidtrader.jobs.eod_report   # Generate reports

# Testing
python -m pytest tests/                 # Run all tests
python tests/test_indicators.py         # Test indicators
python tests/test_strategies.py         # Test strategies
```

## Success Criteria

✅ **Foundation Complete When:**
- Database schema applied
- 500+ S&P 500 symbols loaded
- Basic data ingestion working
- Indicators producing correct values

✅ **Trading System Complete When:**
- Strategies generate buy/sell signals
- Risk management filters working
- Orders generated and stored
- Daily reports produced

✅ **Production Ready When:**
- Automated job scheduling
- Error handling and monitoring
- Performance metrics tracking
- Security measures implemented
