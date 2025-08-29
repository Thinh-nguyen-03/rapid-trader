# RapidTrader Project Structure

Comprehensive overview of the RapidTrader codebase organization and architecture.

## 📁 High-Level Organization

```
rapidtrader-starter-v4.1/
├── 📄 Project Root
│   ├── README.md              # Main project overview
│   ├── pyproject.toml         # Python package configuration
│   ├── PROGRESS.md            # Implementation progress tracking
│   ├── PROJECT_STRUCTURE.md   # This file - project organization
│   └── TASKS.md               # Implementation task breakdown
│
├── 🏗️ rapidtrader/           # Main package directory
│   ├── __init__.py            # Package initialization
│   ├── core/                  # Core infrastructure
│   ├── data/                  # Data acquisition and management
│   ├── indicators/            # Technical analysis functions
│   ├── strategies/            # Trading strategy implementations
│   ├── risk/                  # Risk management systems
│   └── jobs/                  # Automation and job framework
│
├── 📚 docs/                   # Documentation
│   ├── README.md              # Documentation overview
│   ├── FMP_SETUP.md           # Financial Modeling Prep setup
│   ├── MINIMAL_CORE_PACK.md   # Complete implementation guide
│   ├── SUPABASE_SETUP.md      # Database setup instructions
│   ├── environment-setup.md   # Development environment guide
│   ├── rapidtrader_mvp_spec.md # Technical specification
│   ├── mvp_enhancements_addendum.md # Future enhancements
│   ├── runbook.md             # Operations and maintenance
│   ├── technical_trading_primer.md # Technical analysis guide
│   └── LEARNING_PATH/         # Learning resources
│       └── Apply_It_Now.md    # Implementation checklist
│
├── 🔧 scripts/               # Core utility scripts
│   ├── seed_sp500.py          # S&P 500 symbol seeding (Polygon.io)
│   └── setup_db.sql          # Database schema creation
│
├── 🛠️ tools/                 # Development and testing tools
│   └── testing/              # Core system validation scripts
│       ├── README.md          # Testing tools documentation
│       ├── test_database_connection.py # Database connectivity tests
│       └── test_indicator_accuracy.py # Technical indicator validation
│
└── 🧪 tests/                 # Test suite (framework ready)
    └── __init__.py            # Test package initialization
```

## 🏗️ Core Package Architecture

### rapidtrader/core/ - Infrastructure Foundation

**Purpose**: Core system components that everything else depends on.

```
core/
├── __init__.py              # Core module exports
├── config.py                # Configuration management
└── db.py                    # Database connection handling
```

**Key Components**:
- **Configuration Management**: Environment variable handling, parameter validation
- **Database Connection**: SQLAlchemy engine management, connection pooling
- **Logging Setup**: Centralized logging configuration [[memory:6863719]]

**Dependencies**: 
- `pydantic-settings` for configuration
- `sqlalchemy` for database operations
- `python-dotenv` for environment variables

### rapidtrader/data/ - Data Management

**Purpose**: All data acquisition, storage, and retrieval operations.

```
data/
├── __init__.py              # Data module exports  
├── ingest.py                # ✅ OHLCV data ingestion (Polygon.io)
└── sp500_api.py             # ✅ S&P 500 symbol management (Polygon.io/Wikipedia)
```

**Key Components**:
- **Data Ingestion**: Download OHLCV data from Polygon.io with enterprise-grade quality
- **Symbol Management**: S&P 500 constituent tracking via Polygon.io with Wikipedia fallback
- **Data Validation**: Quality checks and error handling
- **Database Storage**: Efficient bulk insert operations

**Data Sources**:
- **Polygon.io**: Primary source for S&P 500 constituents, OHLCV data, real-time market data
- **Wikipedia**: Fallback for S&P 500 constituents (no API key required)
- **Financial Modeling Prep**: Legacy support for S&P 500 constituents

### rapidtrader/indicators/ - Technical Analysis

**Purpose**: Technical indicator calculations for strategy development.

```
indicators/
├── __init__.py              # Indicator module exports
└── core.py                  # ✅ Core indicators (SMA, RSI, ATR)
```

**Key Components**:
- **Simple Moving Average (SMA)**: Trend identification, crossover signals
- **Relative Strength Index (RSI)**: Momentum, overbought/oversold conditions
- **Average True Range (ATR)**: Volatility measurement, position sizing

**Design Principles**:
- Pure functions with no side effects
- Pandas Series input/output for efficiency
- Configurable parameters
- Vectorized calculations for performance

### rapidtrader/strategies/ - Trading Logic

**Purpose**: Trading strategy implementations and signal generation.

```
strategies/          # 🚧 IMPLEMENTATION PENDING
├── __init__.py              # Strategy module exports
├── confirmation.py          # 2-of-3 signal confirmation system
├── rsi_mr.py               # RSI mean-reversion strategy
└── sma_cross.py            # SMA crossover strategy
```

**Planned Components**:
- **RSI Mean-Reversion**: Contrarian strategy using RSI extremes
- **SMA Crossover**: Trend-following using moving average crossovers
- **Signal Confirmation**: 2-of-3 confirmation system for noise reduction
- **Strategy Framework**: Base classes for strategy development

**Strategy Interface**:
```python
def generate_signals(df: pd.DataFrame, **params) -> pd.DataFrame:
    """
    Generate trading signals for a given price series.
    
    Args:
        df: OHLCV DataFrame
        **params: Strategy-specific parameters
        
    Returns:
        DataFrame with columns: ['signal', 'strength', 'metadata']
    """
```

### rapidtrader/risk/ - Risk Management

**Purpose**: Risk control systems and position sizing algorithms.

```
risk/               # 🚧 IMPLEMENTATION PENDING
├── __init__.py              # Risk module exports
├── sizing.py               # Position sizing algorithms
├── controls.py             # Risk controls and filters
└── stop_cooldown.py        # Stop loss management
```

**Planned Components**:
- **Position Sizing**: Fixed-fractional, ATR-based sizing
- **Market Filter**: SPY 200-SMA bull/bear market detection
- **Sector Limits**: Maximum exposure per sector constraints
- **Stop Management**: ATR-based stops with cooldown periods

**Risk Framework**:
- Portfolio-level risk constraints
- Real-time risk monitoring
- Automatic position sizing
- Dynamic risk adjustment

### rapidtrader/jobs/ - Automation Framework

**Purpose**: End-of-day job automation and workflow management.

```
jobs/               # 🚧 IMPLEMENTATION PENDING
├── __init__.py              # Jobs module exports
├── eod_ingest.py           # Daily data ingestion job
├── eod_trade.py            # Signal generation and order creation
└── eod_report.py           # Daily reporting and analytics
```

**Planned Components**:
- **EOD Ingest**: Download and store daily market data
- **EOD Trade**: Generate signals, apply risk controls, create orders
- **EOD Report**: Performance analytics and daily summaries
- **Job Framework**: Scheduling, error handling, logging

**Job Interface**:
```python
class BaseJob:
    def validate_prerequisites(self) -> bool:
        """Check if job can run successfully."""
        
    def execute(self) -> JobResult:
        """Main job execution logic."""
        
    def handle_errors(self, error: Exception) -> None:
        """Error handling and recovery."""
```

## 📚 Documentation Structure

### Core Documentation

- **README.md**: Project overview and quick start
- **FMP_SETUP.md**: Financial Modeling Prep API setup
- **SUPABASE_SETUP.md**: Database configuration guide
- **environment-setup.md**: Complete development environment setup

### Technical Documentation

- **rapidtrader_mvp_spec.md**: Complete technical specification
- **MINIMAL_CORE_PACK.md**: Drop-in implementation reference
- **technical_trading_primer.md**: Technical analysis concepts

### Operational Documentation

- **runbook.md**: Operations, monitoring, and troubleshooting
- **mvp_enhancements_addendum.md**: Future enhancement roadmap

### Learning Resources

- **LEARNING_PATH/Apply_It_Now.md**: Step-by-step implementation checklist

## 🔧 Scripts and Utilities

### Database Management
- **setup_db.sql**: Complete database schema creation
- **seed_sp500.py**: S&P 500 symbol population

### Testing and Validation
- **test_fmp_api.py**: API connectivity and data validation

### Future Scripts (Planned)
- **backtest.py**: Strategy backtesting framework
- **health_check.py**: System health monitoring
- **data_validation.py**: Data quality checks

## 🧪 Testing Strategy

### Test Organization
```
tests/              # 🚧 FRAMEWORK READY
├── __init__.py              # Test package initialization
├── unit/                    # Unit tests for individual components
│   ├── test_indicators.py   # Technical indicator tests
│   ├── test_strategies.py   # Strategy logic tests
│   └── test_risk.py        # Risk management tests
├── integration/             # Integration tests
│   ├── test_data_pipeline.py # End-to-end data flow
│   └── test_jobs.py        # Job execution tests
└── fixtures/               # Test data and mock objects
    ├── sample_data.py      # Sample OHLCV data
    └── mock_apis.py        # Mock API responses
```

### Testing Principles
- **Unit Tests**: Fast, isolated tests for individual functions
- **Integration Tests**: Test component interactions
- **Data Validation**: Verify data quality and consistency
- **Performance Tests**: Ensure acceptable execution times

## 📦 Dependencies and Configuration

### Core Dependencies
```toml
[project]
dependencies = [
    "pandas>=2.2",           # Data manipulation
    "numpy>=1.26",           # Numerical computing
    "polygon-api-client>=1.14.0",  # Market data (Polygon.io)
    "SQLAlchemy>=2.0",       # Database ORM
    "psycopg[binary]>=3.2",  # PostgreSQL adapter
    "pydantic-settings>=2.4", # Configuration
    "python-dotenv>=1.0",    # Environment variables
    "requests>=2.31"         # HTTP requests
]
```

### Optional Dependencies
```toml
[project.optional-dependencies]
dev = [
    "pytest>=7.0",           # Testing framework
    "black>=23.0",           # Code formatting
    "flake8>=6.0",           # Linting
    "mypy>=1.0"              # Type checking
]
```

### Configuration Management
- **Environment Variables**: All parameters configurable via .env
- **Hierarchical Config**: Environment → defaults → overrides
- **Validation**: Pydantic for type checking and validation
- **Security**: Sensitive data in environment variables only

## 🔄 Data Flow Architecture

### Daily Workflow
```
1. Pre-Market (Optional)
   └── Symbol universe updates
   
2. Post-Market (Primary)
   ├── Data Ingestion
   │   ├── Download OHLCV data
   │   └── Update market state
   ├── Signal Generation
   │   ├── Calculate indicators
   │   ├── Generate strategy signals
   │   └── Apply confirmation filters
   ├── Risk Management
   │   ├── Apply market filter
   │   ├── Check sector limits
   │   └── Calculate position sizes
   └── Order Generation
       ├── Create dry-run orders
       └── Store in database
       
3. Evening (Reporting)
   ├── Performance analytics
   ├── Daily reports
   └── System maintenance
```

### Database Schema Flow
```
symbols → bars_daily → indicators → signals_daily → orders_eod
    ↓                                      ↓
market_state ← spy_data            symbol_events ← stops
```

## 🎯 Design Principles

### Code Organization [[memory:6863722]]
- **1-3 files per module**: Keep modules focused and manageable
- **Clear separation of concerns**: Each module has single responsibility
- **Minimal coupling**: Modules interact through well-defined interfaces

### Error Handling
- **Graceful degradation**: System continues operating with partial failures
- **Comprehensive logging**: All errors logged with context [[memory:6863719]]
- **Fail-fast validation**: Catch configuration errors early

### Performance
- **Vectorized operations**: Use pandas/numpy for bulk calculations
- **Database efficiency**: Bulk operations, proper indexing
- **Memory management**: Process data in chunks for large datasets

### Extensibility
- **Plugin architecture**: Easy to add new strategies and indicators
- **Configuration-driven**: Parameters adjustable without code changes
- **Modular design**: Components can be replaced or upgraded independently

## 🚀 Future Architecture Considerations

### Scalability
- **Horizontal scaling**: Support for distributed processing
- **Caching layers**: Redis for frequently accessed data
- **Microservices**: Split into independent services as system grows

### Real-time Capabilities
- **Streaming data**: Support for real-time price feeds
- **Event-driven architecture**: React to market events immediately
- **WebSocket integration**: Real-time dashboard updates

### Advanced Features
- **Machine learning pipeline**: Model training and inference
- **Alternative data**: News, sentiment, economic data integration
- **Multi-asset support**: Forex, crypto, options, futures

This structure provides a solid foundation for the RapidTrader system while maintaining flexibility for future enhancements and scaling.
