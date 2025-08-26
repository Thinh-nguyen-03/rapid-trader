# Financial Modeling Prep (FMP) Setup Guide

Simple guide to get S&P 500 data using Financial Modeling Prep API.

## 🔑 **Get Your Free API Key**

1. Go to: https://financialmodelingprep.com/developer/docs
2. Sign up for a free account
3. Get your API key from the dashboard

**Free Tier:** 250 API calls per day (perfect for S&P 500 data)

## ⚙️ **Configuration**

Add your API key to your `.env` file:

```bash
# .env file
RT_FMP_API_KEY=your_fmp_api_key_here
```

## 🧪 **Test the Setup**

```bash
# Test FMP API connection
python scripts/test_fmp_api.py

# Seed S&P 500 symbols
python scripts/seed_sp500.py
```

## 📊 **What You Get**

- **500+ S&P 500 symbols** with current constituents
- **Sector classifications** (Technology, Healthcare, etc.)
- **Company names** and metadata
- **Automatic updates** when you re-run the script

## 💰 **Cost**

- **Free:** 250 calls/day (enough for weekly S&P 500 updates)
- **Paid:** $14/month for higher limits (if needed for daily updates)

## 🔄 **Usage Pattern**

```bash
# Run once per week to update S&P 500 list
python scripts/seed_sp500.py

# Or clear and reseed completely
python scripts/seed_sp500.py --clear
```

That's it! Simple, reliable, and focused on what you need.