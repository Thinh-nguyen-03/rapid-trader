# Environment Setup Guide

This guide walks you through setting up your `.env` file with all required credentials.

## Quick Start Checklist

- [ ] Get Alpaca credentials (REQUIRED - FREE)
- [ ] Get FMP API key (OPTIONAL - FREE)
- [ ] Create `.env` file
- [ ] Test the connection

---

## Step 1: Get Alpaca API Credentials (REQUIRED - 100% FREE)

Alpaca provides FREE historical market data and paper trading.

### Instructions:

1. **Go to Alpaca website:**
   - Visit: https://alpaca.markets/

2. **Sign up for FREE paper trading:**
   - Click "Get Started" or "Sign Up"
   - Choose "Paper Trading" (completely free, no credit card)
   - Fill in your email and create an account
   - Verify your email

3. **Generate API Keys:**
   - Log in to your Alpaca dashboard
   - Navigate to: **"Your API Keys"** (left sidebar)
   - Click **"Generate New Key"**
   - You'll see two keys:
     - **API Key ID** (looks like: `PKXXXXXXXXXXXXXXX`)
     - **Secret Key** (looks like: `xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`)
   - **IMPORTANT:** Copy both keys immediately - the secret key won't be shown again!

4. **What you'll get:**
   ```
   API Key ID: PKXXXXXXXXXXXXXXX
   Secret Key: xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   ```

### What Alpaca Gives You FREE:
- ✅ Up to 10 years of historical daily data
- ✅ Real-time quotes (with paper account)
- ✅ Paper trading with $100,000 virtual cash
- ✅ Unlimited API calls (within rate limits)
- ✅ No credit card required

---

## Step 2: Get FMP API Key (OPTIONAL - FREE TIER)

Financial Modeling Prep provides company fundamentals and sector data.

### Instructions:

1. **Go to FMP website:**
   - Visit: https://financialmodelingprep.com/developer/docs/

2. **Sign up for free tier:**
   - Click "Get Your Free API Key"
   - Sign up with your email
   - Verify your email

3. **Get your API key:**
   - After verification, you'll see your API key in the dashboard
   - Copy the key (looks like: `xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`)

### What FMP Free Tier Gives You:
- ✅ 250 API requests per day
- ✅ Company profiles (sector, industry)
- ✅ Financial statements
- ✅ Stock prices (historical)

### Do You Need FMP?
- **YES** if you want automatic sector classification for stocks
- **NO** if you're okay with manual sector classification or using cached data
- The system will work without it, but sector data updates will be limited

---

## Step 3: Create Your `.env` File

### Option A: Use Command Line

```bash
# Navigate to your project directory
cd c:\Users\0510t\OneDrive\Documents\rapid-trader

# Copy the example file
copy .env.example .env
```

### Option B: Create Manually

1. Open your project folder in VS Code or File Explorer
2. Create a new file named `.env` (exactly, with the dot at the start)
3. Copy the contents from `.env.example`

### Fill in Your Credentials

Open the `.env` file and update these lines:

```bash
# REQUIRED: Paste your Alpaca credentials here
RT_ALPACA_API_KEY=PKXXXXXXXXXXXXXXX
RT_ALPACA_SECRET_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# OPTIONAL: Paste your FMP API key here (or leave blank)
RT_FMP_API_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### Example of a Complete `.env` File:

```bash
# Database
RT_DB_URL=postgresql+psycopg://postgres:postgres@localhost:5432/rapidtrader

# Alpaca (REQUIRED)
RT_ALPACA_API_KEY=PKABCDEF123456789
RT_ALPACA_SECRET_KEY=abcdefghijklmnopqrstuvwxyz1234567890abcd
RT_ALPACA_PAPER=True
RT_ALPACA_ENDPOINT=https://paper-api.alpaca.markets

# FMP (OPTIONAL)
RT_FMP_API_KEY=1234567890abcdef1234567890abcdef

# Trading Parameters (keep defaults)
RT_MARKET_FILTER_ENABLE=1
RT_MARKET_FILTER_SMA=200
RT_MARKET_FILTER_SYMBOL=SPY
RT_ALLOW_EXITS_IN_BEAR=1
RT_SELLS_HELD_POSITIONS_ONLY=0
RT_ENABLE_SIGNAL_CONFIRM=1
RT_CONFIRM_WINDOW=3
RT_CONFIRM_MIN_COUNT=2
RT_ENABLE_ATR_STOP=1
RT_ATR_LOOKBACK=14
RT_ATR_STOP_K=3.0
RT_COOLDOWN_DAYS_ON_STOP=1
RT_START_CAPITAL=100000.0
RT_PCT_PER_TRADE=0.05
RT_DAILY_RISK_CAP=0.005
RT_MAX_EXPOSURE_PER_SECTOR=0.30
RT_DRAWDOWN_THRESHOLD=-0.12
RT_MAX_PORTFOLIO_HEAT=0.06
RT_PORTFOLIO_HEAT_ENABLE=1
RT_VIX_SCALING_ENABLE=1
RT_VIX_THRESHOLD_ELEVATED=20.0
RT_VIX_THRESHOLD_HIGH=30.0
RT_VIX_SCALE_ELEVATED=0.5
RT_VIX_SCALE_HIGH=0.25
RT_CORRELATION_CHECK_ENABLE=1
RT_CORRELATION_THRESHOLD=0.75
RT_CORRELATION_LOOKBACK=60
RT_CORRELATION_TOP_N=3
```

---

## Step 4: Test Your Configuration

Run the test script to verify everything is working:

```bash
python test_alpaca_migration.py
```

### Expected Output:

```
============================================================
Testing Alpaca Data Migration
============================================================

1. Checking Alpaca credentials...
✅ Alpaca credentials found

2. Testing data fetch for SPY...
Retrieved 30 bars for SPY
✅ Successfully fetched 30 bars for SPY

Sample data:
            Open   High    Low  Close    Volume
date
2025-01-20  600.1  601.5  598.3  600.8  50000000
2025-01-21  601.0  603.2  600.5  602.1  48000000
2025-01-22  602.5  604.8  601.9  603.5  52000000

3. Testing previous close fetch...
✅ Latest close for SPY: $603.50

============================================================
✅ All tests passed! Alpaca migration successful!
============================================================
```

---

## Troubleshooting

### Error: "RT_ALPACA_API_KEY not set in .env"
- Make sure you created a file named `.env` (with the dot)
- Check that the file is in the project root directory
- Verify the API key line doesn't have extra spaces

### Error: "401 Unauthorized" or "Invalid credentials"
- Double-check you copied the API keys correctly
- Make sure you're using **Paper Trading** keys (not live trading)
- Try generating a new key pair in Alpaca dashboard

### Error: "No data returned for SPY"
- Your Alpaca account might not be fully activated yet
- Wait a few minutes and try again
- Check if markets are open (data is only available during market hours or for historical dates)

### FMP API Not Working
- Verify your FMP API key is correct
- Check you haven't exceeded the 250 requests/day limit
- FMP is optional - the system will work without it

---

## Security Notes

⚠️ **IMPORTANT:**
- **NEVER** commit your `.env` file to git
- **NEVER** share your API keys publicly
- The `.env` file is already in `.gitignore`
- If you accidentally expose your keys, regenerate them immediately

---

## Next Steps

Once your `.env` is set up and tested:

1. **Initialize your database:**
   ```bash
   python scripts/init_database.py
   ```

2. **Update symbols and fetch data:**
   ```bash
   python scripts/update_database.py --all
   ```

3. **Start trading (paper mode):**
   ```bash
   python -m rapidtrader.jobs.eod_trade
   ```

---

## Need Help?

- Alpaca Support: https://alpaca.markets/support
- FMP Documentation: https://financialmodelingprep.com/developer/docs/
- RapidTrader Issues: Check the docs/ folder for more guides
