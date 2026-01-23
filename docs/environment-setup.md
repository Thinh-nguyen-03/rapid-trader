# Development Environment Setup

Complete setup guide for RapidTrader development environment.

## Prerequisites

- Python 3.11 or higher
- PostgreSQL or Supabase account
- Git
- Alpaca paper trading account (free)

## Quick Setup

### 1. Clone and Create Virtual Environment

```bash
git clone <repository-url>
cd rapid-trader
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
```

### 2. Install Dependencies

```bash
pip install --upgrade pip
pip install -e .
```

This installs:
- alpaca-py (market data & trading)
- pandas-market-calendars (market holidays)
- requests (FMP API)
- SQLAlchemy, pandas, numpy (core dependencies)

### 3. Configure Environment

See [SETUP_ENV_GUIDE.md](../SETUP_ENV_GUIDE.md) for detailed API setup instructions.

Quick `.env` template:
```bash
# Database
RT_DB_URL=postgresql+psycopg://postgres:postgres@localhost:5432/rapidtrader

# Alpaca API (required - free)
RT_ALPACA_API_KEY=your_alpaca_api_key
RT_ALPACA_SECRET_KEY=your_alpaca_secret_key
RT_ALPACA_PAPER=True
RT_ALPACA_ENDPOINT=https://paper-api.alpaca.markets

# FMP API (optional - for sector data)
RT_FMP_API_KEY=your_fmp_key_or_leave_blank
```

### 4. Database Setup

#### Option A: Supabase (Recommended)
See [SUPABASE_SETUP.md](SUPABASE_SETUP.md) for complete instructions.

#### Option B: Local PostgreSQL
```bash
# Install PostgreSQL
# Create database
createdb rapidtrader

# Run schema (if you have setup script)
psql rapidtrader < scripts/schema.sql
```

### 5. Verify Installation

```bash
# Test Alpaca connection
python test_alpaca_migration.py

# Test database connectivity
python tools/testing/test_database_connection.py

# Load S&P 500 symbols
python scripts/update_database.py --quick
```

## Development Tools

### Code Quality

```bash
# Install dev dependencies
pip install black flake8 mypy pytest

# Format code
black rapidtrader/

# Lint
flake8 rapidtrader/

# Type check
mypy rapidtrader/
```

### Testing

```bash
# Test database
python tools/testing/test_database_connection.py

# Test indicators
python tools/testing/test_indicator_accuracy.py

# Run unit tests (if available)
pytest tests/
```

### Database Management

```bash
# Backup database
pg_dump $RT_DB_URL > backup_$(date +%Y%m%d).sql

# Restore database
psql $RT_DB_URL < backup_20260123.sql

# Check data
python scripts/update_database.py --quick
```

## IDE Configuration

### VS Code (Recommended)

**Extensions:**
- Python (Microsoft)
- PostgreSQL (Chris Kolkman)
- GitLens
- Python Docstring Generator

**.vscode/settings.json:**
```json
{
  "python.formatting.provider": "black",
  "python.linting.enabled": true,
  "python.linting.flake8Enabled": true,
  "python.testing.pytestEnabled": true
}
```

### PyCharm

1. Open project folder
2. Configure interpreter: Settings → Project → Python Interpreter → Select .venv
3. Enable Black formatter: Settings → Tools → Black
4. Configure database: Database tool window → Add PostgreSQL

## Common Issues

### Database Connection Failed
- Check connection string format in `.env`
- Verify PostgreSQL is running: `pg_isready`
- Test with: `python tools/testing/test_database_connection.py`

### API Authentication Error
- Verify Alpaca credentials in `.env`
- Test with: `python test_alpaca_migration.py`
- Regenerate keys if needed at alpaca.markets

### Import Errors
- Ensure package installed: `pip install -e .`
- Activate venv: `source .venv/bin/activate`
- Check Python version: `python --version` (must be 3.11+)

### Missing Dependencies
```bash
# Reinstall all dependencies
pip install --upgrade pip
pip install -e .
```

## Production Considerations

### Environment Variables
- Use secrets manager (AWS Secrets Manager, HashiCorp Vault)
- Never commit `.env` to git
- Rotate API keys quarterly

### Database
- Use managed PostgreSQL (AWS RDS, Supabase)
- Enable SSL connections
- Automated daily backups
- Connection pooling

### Monitoring
- Log to structured format (JSON)
- Monitor API rate limits
- Track system health metrics
- Alert on failures

### Security
- Least privilege database access
- Secure connection strings
- Regular dependency updates: `pip list --outdated`

## Next Steps

1. **API Setup**: Complete [SETUP_ENV_GUIDE.md](../SETUP_ENV_GUIDE.md)
2. **Database**: Configure using [SUPABASE_SETUP.md](SUPABASE_SETUP.md)
3. **Operations**: Read [runbook.md](runbook.md) for daily procedures
4. **Architecture**: Review [rapidtrader_mvp_spec.md](rapidtrader_mvp_spec.md)
