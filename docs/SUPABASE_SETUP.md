# Supabase Setup Instructions

Your RapidTrader Supabase database has been successfully configured!

## 📋 **Your Project Details**
- **Project Name**: rapidtrader-mvp
- **Project ID**: lxwaqpzhxpxzeygnegnv
- **Region**: us-east-1
- **Status**: ACTIVE_HEALTHY
- **Database Host**: db.lxwaqpzhxpxzeygnegnv.supabase.co

## 🔑 **Connection Configuration**

### Step 1: Create .env file
Copy the connection string and create a `.env` file in your project root:

```bash
# Create .env file with your Supabase password
RT_DB_URL=postgresql+psycopg://postgres:YOUR_SUPABASE_PASSWORD@db.lxwaqpzhxpxzeygnegnv.supabase.co:5432/postgres
```

**Important**: Replace `YOUR_SUPABASE_PASSWORD` with the actual password you set when creating the project.

### Step 2: Find Your Password
If you forgot your Supabase password:
1. Go to https://supabase.com/dashboard/project/lxwaqpzhxpxzeygnegnv
2. Settings → Database 
3. Reset Database Password if needed

## ✅ **Database Schema Status**

All tables have been successfully created:

| Table | Purpose | Status |
|-------|---------|--------|
| `symbols` | Symbol universe with sectors | ✅ Created |
| `bars_daily` | OHLCV market data | ✅ Created |
| `signals_daily` | Strategy signals & strength | ✅ Created |
| `orders_eod` | Generated orders (dry-run) | ✅ Created |
| `market_state` | SPY filter cache & metrics | ✅ Created |

## 🧪 **Testing Connection**

After creating your `.env` file, test the connection:

```bash
python tests/test_foundation.py
```

Expected result: All 3 tests should pass (Config ✅, Database ✅, Indicators ✅)

## 🌐 **Supabase Dashboard Access**

- **Project URL**: https://lxwaqpzhxpxzeygnegnv.supabase.co
- **Dashboard**: https://supabase.com/dashboard/project/lxwaqpzhxpxzeygnegnv
- **Table Editor**: https://supabase.com/dashboard/project/lxwaqpzhxpxzeygnegnv/editor

## ✅ **Setup Status: COMPLETE**

1. ✅ Create `.env` file with your password
2. ✅ Test database connection 
3. ✅ Add sample symbols to `symbols` table (6 symbols added)
4. ⏳ Implement data ingestion pipeline
5. ⏳ Build trading strategies

## 🎯 **Connection Verified**

**Test Results (2025-01-27):**
- ✅ Database connection: SUCCESS
- ✅ Found tables: bars_daily, market_state, orders_eod, signals_daily, symbols
- ✅ All required tables exist

## 📊 **Sample Data Added**

| Symbol | Sector |
|--------|--------|
| SPY | ETF |
| AAPL | Technology |
| MSFT | Technology |
| GOOGL | Technology |
| TSLA | Consumer Discretionary |
| NVDA | Technology |

Your Supabase database is **fully operational** and ready for RapidTrader development!
