# S&P 500 Data Source Architecture

## Overview

The RapidTrader system now uses **iShares Core S&P 500 ETF (IVV)** as the primary data source for S&P 500 constituents, replacing the previous hardcoded list. This provides:

- ✅ **Official data** from BlackRock's iShares ETF holdings
- ✅ **Daily updates** with actual S&P 500 constituents
- ✅ **Automatic sector classification** from official GICS sectors
- ✅ **Market cap weighting** for position sizing
- ✅ **Intelligent caching** with configurable TTL
- ✅ **Automatic fallback** to hardcoded list if iShares is unavailable

## Architecture

### Data Flow

```
iShares API (Primary)
    ↓
CSV Download → Parse → Validate → Cache (PostgreSQL)
    ↓                                    ↓
Application ← Load from Cache ← Check Freshness
    ↓
Fallback (Hardcoded ~100 symbols) ← If iShares fails
```

### Components

#### 1. iSharesClient (`rapidtrader/data/sp500_api.py`)

Professional API client with:
- **Retry logic** using `@retry_api_call` decorator (3 attempts with exponential backoff)
- **Request timeout** (configurable, default 30s)
- **CSV parsing** with header detection and data validation
- **Database caching** with automatic table creation
- **TTL management** (configurable, default 7 days)

#### 2. Database Table: `sp500_constituents`

```sql
CREATE TABLE sp500_constituents (
    symbol TEXT PRIMARY KEY,
    name TEXT,
    sector TEXT NOT NULL,
    weight DECIMAL(10, 6),
    source TEXT DEFAULT 'ishares',
    last_updated DATE NOT NULL DEFAULT CURRENT_DATE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_sp500_last_updated ON sp500_constituents(last_updated);
```

#### 3. Configuration Settings (`rapidtrader/core/config.py`)

```python
# S&P 500 Constituents - iShares ETF data source
RT_SP500_SOURCE: str = "ishares"  # Options: ishares, hardcoded
RT_SP500_ISHARES_URL: str = "https://www.ishares.com/us/products/239726/..."
RT_SP500_CACHE_TTL_DAYS: int = 7  # Refresh S&P 500 list weekly
RT_SP500_REQUEST_TIMEOUT: int = 30  # HTTP timeout in seconds
```

## Usage

### Basic Usage

```python
from rapidtrader.data.sp500_api import get_sp500_symbols

# Get S&P 500 symbols (uses cache if fresh)
symbols = get_sp500_symbols()
# Returns: [('AAPL', 'Technology'), ('MSFT', 'Technology'), ...]

# Force refresh from iShares (skip cache)
symbols = get_sp500_symbols(force_refresh=True)
```

### Advanced Usage with iSharesClient

```python
from rapidtrader.data.sp500_api import iSharesClient

# Create client
client = iSharesClient()

# Fetch fresh data from iShares
df = client.get_constituents()
print(df.head())
#   symbol                          name                     sector  weight
# 0   NVDA                   NVIDIA CORP  Information Technology   7.59
# 1   AAPL                     APPLE INC  Information Technology   6.20
# 2   MSFT                MICROSOFT CORP  Information Technology   5.67

# Use cached data (respects TTL)
df = client.get_constituents_with_cache()

# Force refresh and update cache
df = client.get_constituents_with_cache(force_refresh=True)
```

### CLI Usage

```bash
# Update S&P 500 symbols from iShares (uses cache if fresh)
python scripts/update_database.py --symbols

# Force refresh from iShares (skip cache)
python scripts/update_database.py --symbols --force-refresh

# Full database update with fresh S&P 500 data
python scripts/update_database.py --all --force-refresh

# Quick update (skip SIC rebuild)
python scripts/update_database.py --quick
```

## Configuration

### Environment Variables (.env)

```bash
# Data source mode (ishares or hardcoded)
RT_SP500_SOURCE=ishares

# Custom iShares URL (optional, has working default)
RT_SP500_ISHARES_URL=https://www.ishares.com/us/products/239726/ishares-core-sp-500-etf/1467271812596.ajax?fileType=csv&fileName=IVV_holdings&dataType=fund

# Cache TTL in days (default: 7)
RT_SP500_CACHE_TTL_DAYS=7

# HTTP timeout in seconds (default: 30)
RT_SP500_REQUEST_TIMEOUT=30
```

### Switching to Hardcoded Mode

If iShares becomes unavailable, you can force hardcoded mode:

```bash
# In .env file
RT_SP500_SOURCE=hardcoded
```

The hardcoded fallback contains ~100 major S&P 500 constituents by market cap, ensuring basic functionality.

## Caching Strategy

### Cache Lifecycle

1. **First Request**: Fetch from iShares → Store in database
2. **Subsequent Requests**: Load from cache if `last_updated` < TTL
3. **Cache Expiry**: Automatically fetch fresh data when TTL exceeded
4. **Force Refresh**: Skip cache with `force_refresh=True`

### Cache Invalidation

```python
# Automatic (based on TTL)
symbols = get_sp500_symbols()  # Uses cache if < 7 days old

# Manual (force refresh)
symbols = get_sp500_symbols(force_refresh=True)

# CLI force refresh
python scripts/update_database.py --symbols --force-refresh
```

### Cache Monitoring

```sql
-- Check cache status
SELECT
    COUNT(*) as total_symbols,
    MAX(last_updated) as last_update,
    MIN(last_updated) as oldest_update,
    COUNT(DISTINCT sector) as sector_count
FROM sp500_constituents;

-- View cached constituents
SELECT symbol, sector, weight, last_updated
FROM sp500_constituents
ORDER BY weight DESC
LIMIT 10;
```

## Error Handling

### Retry Logic

All iShares API calls use `@retry_api_call`:
- **3 attempts** with exponential backoff
- **Backoff**: 2s → 4s → 8s → 16s (max 30s)
- **Retries on**: Network errors, timeouts, HTTP 5xx errors
- **No retry on**: HTTP 4xx errors (client errors)

### Fallback Strategy

```python
if RT_SP500_SOURCE != "hardcoded":
    try:
        # Attempt iShares fetch
        return fetch_from_ishares()
    except Exception:
        # Automatic fallback to hardcoded
        logger.warning("Using hardcoded fallback")
        return hardcoded_symbols()
else:
    # Direct hardcoded mode
    return hardcoded_symbols()
```

### Error Scenarios

| Scenario | Behavior |
|----------|----------|
| iShares timeout | Retry 3x → Fallback to hardcoded |
| iShares 404/403 | Immediate fallback to hardcoded |
| CSV parse error | Retry 3x → Fallback to hardcoded |
| Cache DB error | Skip cache, fetch from iShares |
| Both sources fail | Raise `RuntimeError` with details |

## Data Quality

### Validation Rules

1. **Equity Filter**: Only assets with `Asset Class = Equity`
2. **Symbol Validation**: Non-empty, uppercase, no special chars (except `.`)
3. **Sector Mapping**: Map iShares sectors to GICS standard
4. **SPY Requirement**: Always ensure SPY is present (market filter)
5. **Weight Validation**: Numeric, 0-100 range

### Sector Standardization

iShares sectors are mapped to standard GICS sectors:

```python
iShares Sector              → GICS Sector
"Information Technology"    → "Technology"
"Health Care"               → "Healthcare"
"Consumer Discretionary"    → "Consumer Discretionary"
# ... etc
```

## Performance

### Metrics

- **Cache Hit**: ~5ms (database query)
- **Cache Miss**: ~2-3s (iShares CSV fetch + parse)
- **CSV Size**: ~50KB (500+ symbols)
- **Parse Time**: ~100-200ms
- **Database Write**: ~500ms (upsert 500 symbols)

### Optimization

- **Connection Pooling**: 10 base + 20 overflow connections
- **Index**: `idx_sp500_last_updated` for fast freshness checks
- **Batch Upsert**: Single transaction for all symbols
- **Parallel Safe**: Thread-safe database operations

## Testing

### Unit Tests

```bash
# Run iShares client tests
pytest tests/unit/test_ishares_client.py -v

# Test with coverage
pytest tests/unit/test_ishares_client.py --cov=rapidtrader.data.sp500_api
```

### Integration Tests

```bash
# Test full pipeline
python -c "
from rapidtrader.data.sp500_api import get_sp500_symbols
symbols = get_sp500_symbols(force_refresh=True)
print(f'Fetched {len(symbols)} symbols from iShares')
assert len(symbols) >= 500, 'Missing symbols!'
print('✓ Integration test passed')
"
```

### Manual Testing

```bash
# Test iShares fetch
python scripts/update_database.py --symbols --force-refresh

# Verify in database
psql -d rapidtrader -c "SELECT COUNT(*), MAX(last_updated) FROM sp500_constituents;"
```

## Monitoring & Observability

### Structured Logging

All operations emit structured logs:

```python
logger.info("ishares_fetch_start", url=self.url)
logger.info("ishares_fetch_success", bytes=len(response.content))
logger.warning("ishares_fetch_failed_using_fallback", error=str(e))
logger.info("sp500_symbols_loaded", source="ishares", count=len(result))
```

### Log Analysis

```bash
# View iShares operations
grep "ishares" logs/rapidtrader.log | jq

# Monitor failures
grep "fallback" logs/rapidtrader.log

# Cache hit rate
grep "sp500_cache" logs/rapidtrader.log | jq -s 'group_by(.event)[] | {event: .[0].event, count: length}'
```

## Migration Guide

### From Hardcoded to iShares

1. **Update `.env`**:
   ```bash
   RT_SP500_SOURCE=ishares
   RT_SP500_CACHE_TTL_DAYS=7
   ```

2. **Initial fetch**:
   ```bash
   python scripts/update_database.py --symbols --force-refresh
   ```

3. **Verify**:
   ```sql
   SELECT COUNT(*), source FROM sp500_constituents GROUP BY source;
   ```

### Rollback to Hardcoded

1. **Update `.env`**:
   ```bash
   RT_SP500_SOURCE=hardcoded
   ```

2. **Restart services** - no code changes needed

## Production Considerations

### Reliability

- ✅ **Retry logic** on transient failures
- ✅ **Automatic fallback** to hardcoded list
- ✅ **Database caching** reduces API dependency
- ✅ **Connection pooling** prevents DB exhaustion
- ✅ **Request timeout** prevents hanging

### Security

- ✅ **HTTPS only** for iShares requests
- ✅ **User-Agent header** to identify requests
- ✅ **No authentication required** (public data)
- ✅ **SQL injection protection** via parameterized queries

### Compliance

- ✅ **Rate limiting**: ~1 request per 7 days (with caching)
- ✅ **Terms of service**: Public data, no scraping restrictions
- ✅ **Attribution**: Official iShares data source

## Troubleshooting

### "iShares fetch failed"

**Cause**: Network issues, iShares downtime, blocked IP

**Solution**:
1. Check network connectivity
2. Verify URL in logs
3. Try manual curl: `curl -I <ishares_url>`
4. Temporary: Use hardcoded mode

### "Cache table does not exist"

**Cause**: Database migration not run

**Solution**:
```python
from rapidtrader.data.sp500_api import iSharesClient
client = iSharesClient()
client._ensure_cache_table()  # Creates table
```

### "Missing required columns in CSV"

**Cause**: iShares changed CSV format

**Solution**:
1. Check CSV structure: `curl <ishares_url> | head -20`
2. Update column mapping in `parse_csv()`
3. Report issue to maintainers

## References

- **iShares IVV Product Page**: https://www.ishares.com/us/products/239726/ishares-core-sp-500-etf
- **S&P 500 Index**: https://www.spglobal.com/spdji/en/indices/equity/sp-500/
- **GICS Sectors**: https://www.msci.com/gics

## Changelog

### v2.0.0 (2026-01-24)
- ✨ **Feature**: iShares API integration as primary data source
- ✨ **Feature**: Database-backed caching with TTL
- ✨ **Feature**: Automatic fallback to hardcoded list
- ✨ **Feature**: Configurable data source mode
- 🐛 **Fix**: Removed hardcoded 100-symbol limit
- 📝 **Docs**: Comprehensive SP500 data source documentation
- ✅ **Tests**: Unit tests for iSharesClient
