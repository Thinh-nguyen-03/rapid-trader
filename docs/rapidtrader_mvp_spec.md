# RapidTrader MVP Specification

Complete technical specification for the RapidTrader Minimum Viable Product (MVP).

## Executive Summary

RapidTrader is an end-of-day (EOD) algorithmic trading system designed for systematic equity trading. The MVP focuses on S&P 500 stocks using technical analysis strategies with comprehensive risk management.

### Implementation Status
- **Database Infrastructure**: Supabase operational with all tables
- **Data Pipeline**: 505 S&P 500 symbols, 125K+ historical bars
- **Technical Indicators**: All indicators tested and production ready
- **Trading Strategies**: RSI mean-reversion + SMA crossover with confirmation
- **Risk Management**: Market filter, sector caps, position sizing, stop cooldowns
- **Job Framework**: Complete EOD automation pipeline

### Key Objectives
- **Systematic Trading**: Automated signal generation and order creation
- **Risk Management**: Portfolio-level risk controls and position sizing
- **Simplicity**: Clean, maintainable codebase with minimal dependencies
- **Extensibility**: Modular design for easy strategy addition
- **Enterprise-Grade Data**: Professional quality data via Polygon.io

### Target Users
- Individual quantitative traders
- Small hedge funds and family offices
- Trading system developers
- Finance students and researchers

## System Requirements

### Functional Requirements

#### FR1: Data Management
- **FR1.1**: Fetch and maintain S&P 500 constituent list (505 symbols loaded)
- **FR1.2**: Download daily OHLCV data for all symbols (125K+ bars collected)
- **FR1.3**: Store data in relational database with proper schema (Supabase operational)
- **FR1.4**: Handle data quality issues and missing data (100% symbol coverage)
- **FR1.5**: Support historical data backfill (365+ days, 1+ years of data)

#### FR2: Technical Analysis
- **FR2.1**: Calculate Simple Moving Averages (SMA)
- **FR2.2**: Calculate Relative Strength Index (RSI) with Wilder's smoothing
- **FR2.3**: Calculate Average True Range (ATR)
- **FR2.4**: Support configurable parameters for all indicators
- **FR2.5**: Efficient calculation on large datasets (vectorized pandas operations)

#### FR3: Trading Strategies
- **FR3.1**: RSI Mean-Reversion Strategy
  - Buy signals when RSI < 30 (oversold)
  - Sell signals when RSI > 70 (overbought)
  - 2-of-3 confirmation window for signal strength
- **FR3.2**: SMA Crossover Strategy
  - Buy signals when SMA20 > SMA50
  - Sell signals when SMA20 < SMA50
  - Configurable SMA periods
- **FR3.3**: Signal Confirmation System
  - Combine multiple strategy signals
  - Require minimum confirmation count
  - Configurable confirmation window

#### FR4: Risk Management
- **FR4.1**: Position Sizing
  - Fixed-fractional sizing (default 5% per trade)
  - ATR-based target sizing for volatility adjustment
  - Portfolio-level risk constraints
- **FR4.2**: Market Filter
  - SPY 200-SMA bull/bear market detection
  - Disable new entries during bear markets
  - Cache SPY data for performance
- **FR4.3**: Sector Exposure Limits
  - Maximum 30% exposure per sector
  - Real-time sector exposure calculation
  - Block trades exceeding sector limits
- **FR4.4**: Stop Loss Management
  - ATR-based stops (3x ATR default)
  - Stop cooldown period (1 day default)
  - Track stop events in database

#### FR5: Order Management
- **FR5.1**: Generate dry-run orders based on signals
- **FR5.2**: Store all orders with full audit trail
- **FR5.3**: Support basic order types (market orders)
- **FR5.4**: Calculate position quantities based on risk rules
- **FR5.5**: Order validation and constraint checking

#### FR6: Job Framework
- **FR6.1**: EOD Data Ingestion Job
  - Download latest OHLCV data
  - Update market state (SPY cache)
  - Handle API failures gracefully
- **FR6.2**: EOD Trading Job
  - Generate signals for all symbols
  - Apply risk filters and constraints
  - Create orders for valid signals
  - Update position tracking
- **FR6.3**: EOD Reporting Job
  - Generate daily performance summary
  - Calculate portfolio metrics
  - Track filtering statistics
  - Export results to files/email

### Non-Functional Requirements

#### NFR1: Performance
- **NFR1.1**: Process 500+ symbols in < 10 minutes
- **NFR1.2**: Calculate indicators for 365 days of data in < 1 second per symbol
- **NFR1.3**: Database queries execute in < 100ms for typical operations
- **NFR1.4**: Memory usage < 2GB for full system operation

#### NFR2: Reliability
- **NFR2.1**: 99.5% uptime for daily job execution
- **NFR2.2**: Graceful handling of API failures and network issues
- **NFR2.3**: Data integrity validation and corruption detection
- **NFR2.4**: Automatic retry logic for transient failures

#### NFR3: Maintainability
- **NFR3.1**: Modular architecture with clear separation of concerns
- **NFR3.2**: Comprehensive logging for debugging and monitoring
- **NFR3.3**: Configuration-driven parameters (no hardcoded values)
- **NFR3.4**: Unit test coverage > 80% for core functionality

#### NFR4: Scalability
- **NFR4.1**: Support for 1000+ symbols without major refactoring
- **NFR4.2**: Database schema supports multiple timeframes
- **NFR4.3**: Plugin architecture for additional strategies
- **NFR4.4**: Horizontal scaling capability for compute-intensive tasks

## System Architecture

### High-Level Components

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Data Sources  │────│  RapidTrader    │────│   Database      │
│                 │    │     Core        │    │                 │
│ • Polygon.io    │    │                 │    │ • PostgreSQL    │
│ • Wikipedia     │    │ • Indicators    │    │ • Supabase      │
│                 │    │ • Strategies    │    │                 │
└─────────────────┘    │ • Risk Mgmt     │    └─────────────────┘
                       │ • Jobs          │
                       └─────────────────┘
                               │
                       ┌─────────────────┐
                       │   Outputs       │
                       │                 │
                       │ • Orders        │
                       │ • Reports       │
                       │ • Alerts        │
                       └─────────────────┘
```

### Module Structure

```
rapidtrader/
├── core/                 # Core infrastructure
│   ├── config.py        # Configuration management
│   ├── db.py            # Database connection
│   └── market_state.py  # Market regime detection
├── data/                # Data acquisition and management
│   ├── ingest.py        # OHLCV data ingestion
│   └── sp500_api.py     # S&P 500 symbol management
├── indicators/          # Technical analysis
│   └── core.py          # SMA, RSI, ATR implementations
├── strategies/          # Trading strategies
│   ├── confirmation.py  # Signal confirmation logic
│   ├── rsi_mr.py       # RSI mean-reversion
│   └── sma_cross.py    # SMA crossover
├── risk/               # Risk management
│   ├── sizing.py       # Position sizing algorithms
│   ├── controls.py     # Risk controls and filters
│   └── stop_cooldown.py # Stop management
└── jobs/               # Automation framework
    ├── eod_ingest.py   # Daily data ingestion
    ├── eod_trade.py    # Signal generation and orders
    └── eod_report.py   # Reporting and analytics
```

### Database Schema

#### Core Tables

```sql
-- Symbol universe with sector classification
CREATE TABLE symbols (
    symbol TEXT PRIMARY KEY,
    name TEXT,
    sector TEXT,
    sub_sector TEXT,
    is_active BOOLEAN DEFAULT true,
    date_added DATE DEFAULT CURRENT_DATE
);

-- Daily OHLCV bars
CREATE TABLE bars_daily (
    symbol TEXT,
    d DATE,
    open REAL NOT NULL,
    high REAL NOT NULL,
    low REAL NOT NULL,
    close REAL NOT NULL,
    volume INTEGER NOT NULL,
    PRIMARY KEY (symbol, d),
    FOREIGN KEY (symbol) REFERENCES symbols(symbol)
);

-- Trading signals with strength
CREATE TABLE signals_daily (
    d DATE NOT NULL,
    symbol TEXT NOT NULL,
    strategy TEXT NOT NULL,
    direction TEXT NOT NULL,
    strength REAL,
    metadata JSONB,
    PRIMARY KEY (d, symbol, strategy),
    FOREIGN KEY (symbol) REFERENCES symbols(symbol)
);

-- Generated orders (dry-run)
CREATE TABLE orders_eod (
    id SERIAL PRIMARY KEY,
    d DATE NOT NULL,
    symbol TEXT NOT NULL,
    side TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    order_type TEXT NOT NULL,
    price REAL,
    reason TEXT,
    strategy TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (symbol) REFERENCES symbols(symbol)
);

-- Position tracking
CREATE TABLE positions (
    symbol TEXT PRIMARY KEY,
    quantity INTEGER NOT NULL,
    avg_price REAL NOT NULL,
    sector TEXT,
    entry_date DATE,
    stop_price REAL,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (symbol) REFERENCES symbols(symbol)
);

-- Market state cache (SPY data)
CREATE TABLE market_state (
    d DATE PRIMARY KEY,
    spy_close REAL NOT NULL,
    spy_sma200 REAL,
    bull_gate BOOLEAN,
    volume_avg_20d REAL,
    volatility_20d REAL,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Stop loss events and cooldown tracking
CREATE TABLE symbol_events (
    id SERIAL PRIMARY KEY,
    symbol TEXT NOT NULL,
    event_type TEXT NOT NULL,
    d DATE NOT NULL,
    price REAL,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (symbol) REFERENCES symbols(symbol)
);
```

### Data Flow

#### Daily Workflow
1. **Pre-Market (6:00 AM ET)**
   - Check for new S&P 500 constituents
   - Validate previous day's data completeness
   - Update symbol universe if needed

2. **Post-Market (6:00 PM ET)**
   - Download OHLCV data for all symbols
   - Update SPY market state cache
   - Calculate technical indicators
   - Generate trading signals
   - Apply risk filters
   - Create orders
   - Generate daily report

3. **Evening (8:00 PM ET)**
   - Validate all data and calculations
   - Send summary reports
   - Archive logs and clean up temporary files

## Technical Implementation

### Configuration Management

All system parameters configurable via environment variables:

```python
# Database
RT_DB_URL: Database connection string

# Market Filter
RT_MARKET_FILTER_ENABLE: Enable/disable SPY market filter
RT_MARKET_FILTER_SMA: SMA period for market filter (default 200)
RT_MARKET_FILTER_SYMBOL: Symbol for market filter (default SPY)

# Signal Confirmation
RT_ENABLE_SIGNAL_CONFIRM: Enable 2-of-3 confirmation
RT_CONFIRM_WINDOW: Confirmation window in days (default 3)
RT_CONFIRM_MIN_COUNT: Minimum confirmations required (default 2)

# Risk Management
RT_START_CAPITAL: Starting capital amount
RT_PCT_PER_TRADE: Fixed percentage per trade (default 0.05)
RT_DAILY_RISK_CAP: Daily risk limit (default 0.005)
RT_MAX_EXPOSURE_PER_SECTOR: Maximum sector exposure (default 0.30)

# ATR Stops
RT_ENABLE_ATR_STOP: Enable ATR-based stops
RT_ATR_LOOKBACK: ATR calculation period (default 14)
RT_ATR_STOP_K: ATR stop multiplier (default 3.0)
RT_COOLDOWN_DAYS_ON_STOP: Stop cooldown period (default 1)

# API Configuration
RT_POLYGON_API_KEY: Polygon.io API key
```

### Error Handling Strategy

#### Data Source Failures
- Primary: Polygon.io API for all market data
- Fallback: Wikipedia for S&P 500 symbols
- Fallback: Skip symbol and log error for OHLCV data
- Emergency: Static symbol list for system continuity

#### Database Failures
- Retry logic with exponential backoff
- Transaction rollback on partial failures
- Connection pooling for reliability
- Regular health checks

#### Strategy Calculation Errors
- Skip symbol and continue processing
- Log detailed error information
- Maintain processing statistics
- Alert on high error rates

### Performance Optimization

#### Database Optimization
- Proper indexing on frequently queried columns
- Bulk insert operations for large datasets
- Connection pooling for concurrent access
- Query optimization and explain plans

#### Calculation Optimization
- Vectorized operations using pandas/numpy
- Caching of expensive calculations
- Parallel processing for independent calculations
- Memory-efficient data structures

#### API Rate Limiting
- Respect API rate limits with delays
- Batch API calls where possible
- Cache responses to reduce API calls
- Monitor API usage and costs

## Testing Strategy

### Unit Testing
- All indicator calculations with known test cases
- Strategy signal generation with sample data
- Risk management constraint checking
- Database operations with test fixtures

### Integration Testing
- End-to-end data pipeline testing
- API integration testing with mock responses
- Database schema migration testing
- Job framework execution testing

### Performance Testing
- Load testing with 500+ symbols
- Memory usage profiling
- Database query performance
- API response time monitoring

### Validation Testing
- Indicator accuracy against external sources
- Strategy backtest validation
- Risk constraint enforcement
- Data quality validation

## Success Metrics

### System Performance
- **Data Completeness**: >99% of expected symbols have daily data
- **Job Success Rate**: >99.5% successful daily job execution
- **Processing Time**: Complete EOD workflow in <30 minutes
- **Memory Usage**: Peak memory <2GB during processing

### Trading System Quality
- **Signal Generation**: Produce signals for >10% of universe daily
- **Risk Compliance**: 100% adherence to risk constraints
- **Data Quality**: <0.1% data errors or anomalies
- **Audit Trail**: Complete transaction history for all decisions

### Operational Excellence
- **Uptime**: >99.5% system availability during market hours
- **Error Rate**: <0.1% unhandled exceptions
- **Alert Response**: Critical issues detected within 5 minutes
- **Recovery Time**: System restoration within 1 hour of failure

## Deployment Strategy

### Development Environment
- Local PostgreSQL or Supabase
- Python virtual environment
- Git version control
- IDE with debugging support

### Staging Environment
- Cloud database (Supabase/AWS RDS)
- Containerized application
- Automated testing pipeline
- Production-like data volume

### Production Environment
- Managed database service
- Container orchestration (optional)
- Monitoring and alerting
- Automated backup and recovery

### Release Process
1. Feature development in branches
2. Pull request review and testing
3. Staging deployment and validation
4. Production deployment with rollback plan
5. Post-deployment monitoring and validation

## Future Roadmap

### Phase 1 Extensions (Months 2-3)
- Additional technical indicators
- Machine learning strategy framework
- Real-time data integration
- Web-based dashboard

### Phase 2 Extensions (Months 4-6)
- Multi-asset class support
- Advanced risk management
- Broker API integration
- Mobile application

### Phase 3 Extensions (Months 7+)
- Alternative data sources
- Advanced execution algorithms
- Portfolio optimization
- Regulatory compliance features

## Assumptions and Constraints

### Assumptions
- Trading occurs only during US market hours
- Focus on liquid S&P 500 stocks only
- End-of-day trading strategies only
- USD-denominated assets only
- No options or derivatives trading

### Constraints
- Maximum 1,000 API calls per month (Polygon.io free tier)
- PostgreSQL database limitations
- Single-threaded processing for simplicity
- No real-time data requirements
- Dry-run orders only (no actual trading)

### Dependencies
- Polygon.io API availability
- Wikipedia data accessibility
- PostgreSQL/Supabase service uptime
- Python ecosystem stability
- Internet connectivity for data sources

This specification provides the foundation for implementing a robust, scalable algorithmic trading system focused on systematic equity strategies with comprehensive risk management.
