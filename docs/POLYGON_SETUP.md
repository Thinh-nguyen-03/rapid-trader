# Polygon.io Setup Guide

Simple guide to get high-quality financial data using Polygon.io API.

## 🔑 **Get Your Polygon.io API Key**

1. Go to: https://polygon.io/
2. Sign up for an account
3. Get your API key from the dashboard

**Recommended:** Stocks Starter subscription for unlimited API calls and 5 years of historical data
**Alternative:** Free tier (1,000 API calls per month) for basic testing

## ⚙️ **Configuration**

Add your API key to your `.env` file:

```bash
# .env file
RT_POLYGON_API_KEY=your_polygon_api_key_here
```

## 🧪 **Test the Setup**

```bash
# Test database connectivity
python tools/testing/test_database_connection.py

# Test indicator calculations with real data
python tools/testing/test_indicator_accuracy.py

# Seed S&P 500 symbols (uses Polygon.io by default)
python scripts/seed_sp500.py

# Or specify the source explicitly
python scripts/seed_sp500.py --source polygon
```

## 📊 **What You Get**

- **500+ S&P 500 symbols** with current constituents
- **High-quality OHLCV data** with real-time updates
- **Sector classifications** (Technology, Healthcare, etc.)
- **Company metadata** and fundamentals
- **Historical data** going back years

## 💰 **Cost**

- **Free:** 1,000 calls/month (enough for daily S&P 500 EOD updates)
- **Basic:** $99/month for higher limits and real-time data
- **Professional:** $399/month for advanced features

## 🔄 **Usage Pattern**

```bash
# Daily EOD data ingestion (using Polygon.io)
python -m rapidtrader.jobs.eod_ingest

# Update S&P 500 symbol list (weekly, now defaults to Polygon.io)
python scripts/seed_sp500.py

# Historical data backfill (for individual symbols)
python -c "from rapidtrader.data.ingest import ingest_symbol; ingest_symbol('AAPL', days=365)"

# Test data ingestion for a few symbols
python scripts/test_polygon_api.py
```

## 🚀 **Why Polygon.io?**

- **Enterprise-grade data quality** - Used by hedge funds and trading firms
- **Real-time and historical data** - Complete market coverage
- **RESTful API** - Easy integration with clean JSON responses
- **Rate limits are generous** - Free tier supports production use
- **Excellent documentation** - Clear API reference with examples

## 📚 **API Documentation**

- **Main API Docs**: https://polygon.io/docs/stocks/getting-started
- **Stocks API**: https://polygon.io/docs/stocks/rest/getting-started
- **Reference Data**: https://polygon.io/docs/stocks/rest/reference/tickers
- **Market Data**: https://polygon.io/docs/stocks/rest/market-data/aggregates

## 🔧 **Common Endpoints**

### Get S&P 500 Symbols
```
GET /v3/reference/tickers?market=stocks&active=true&limit=1000
```

### Get Daily Bars (OHLCV)
```
GET /v2/aggs/ticker/{symbol}/range/1/day/{from}/{to}
```

### Get Company Details
```
GET /v3/reference/tickers/{symbol}
```

That's it! Professional-grade data for your trading system.
