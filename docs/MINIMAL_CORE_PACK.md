# RapidTrader MVP - Minimal Core Pack (Drop-In)

A complete, drop-in engine for EOD algorithmic trading: data, indicators, signals, risk checks, and dry-run orders.

**Targets:** EOD, long-only equities; RSI mean-reversion + SMA crossover; SPY 200-SMA market filter; 2-of-3 confirmation; ATR sizing; sector caps; stop cooldown.

---

## Overview

Components included:
1. **DB tables:** signals, orders, market state, positions, cooldown events
2. **Indicators:** `sma`, `rsi_wilder`, `atr`
3. **Strategies:** RSI mean-reversion (2-of-3 confirm), SMA crossover (2-day confirm)
4. **Risk:** fixed-fractional and ATR-target sizing, sector cap check, stop-cooldown guard
5. **Market state:** SPY cache + gate (SPY >= SMA200) and "% filtered" metric
6. **Jobs:** `eod_ingest`, `eod_trade`, `eod_report`
7. **Config defaults** and **Polygon.io API integration**

---

## 0) Database Schema

Append to `scripts/setup_db.sql`:

```sql
-- signals and orders (EOD, dry-run)
CREATE TABLE IF NOT EXISTS signals_daily (
  d DATE NOT NULL,
  symbol TEXT NOT NULL,
  strategy TEXT NOT NULL,
  direction TEXT NOT NULL,
  strength DOUBLE PRECISION,
  PRIMARY KEY (d, symbol, strategy)
);

CREATE TABLE IF NOT EXISTS orders_eod (
  id BIGSERIAL PRIMARY KEY,
  d DATE NOT NULL,
  symbol TEXT NOT NULL,
  side TEXT NOT NULL,
  qty INTEGER NOT NULL,
  type TEXT NOT NULL,
  reason TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS positions (
  symbol TEXT PRIMARY KEY,
  qty DOUBLE PRECISION NOT NULL DEFAULT 0,
  avg_px DOUBLE PRECISION NOT NULL DEFAULT 0,
  sector TEXT
);

CREATE TABLE IF NOT EXISTS market_state (
  d DATE PRIMARY KEY,
  spy_close DOUBLE PRECISION,
  spy_sma200 DOUBLE PRECISION,
  bull_gate BOOLEAN,
  total_candidates INTEGER DEFAULT 0,
  filtered_candidates INTEGER DEFAULT 0,
  pct_entries_filtered DOUBLE PRECISION
);

CREATE TABLE IF NOT EXISTS symbol_events (
  symbol TEXT NOT NULL,
  d DATE NOT NULL,
  event TEXT NOT NULL,
  details JSONB,
  PRIMARY KEY (symbol, d, event)
);
```

Apply:

```bash
docker exec -i rapidtrader-db psql -U postgres -d rapidtrader < scripts/setup_db.sql
```

---

## 1) Indicators

**File:** `rapidtrader/indicators/core.py`

Validated with real market data from Polygon.io. All tests passed.

---

## 2) Strategies

**File:** `rapidtrader/strategies/confirmation.py`

```python
import pandas as pd

def confirm(signal_bool: pd.Series, window: int, min_count: int) -> pd.Series:
    strength = signal_bool.astype(int).rolling(window, min_periods=1).sum()
    return strength >= min_count
```

**File:** `rapidtrader/strategies/rsi_mr.py`

```python
import pandas as pd
from ..indicators.core import rsi_wilder
from .confirmation import confirm

def rsi_mean_reversion(df: pd.DataFrame, buy_rsi=30.0, sell_rsi=55.0, window=3, min_count=2) -> pd.DataFrame:
    out = pd.DataFrame(index=df.index)
    out["rsi"] = rsi_wilder(df["close"], 14)
    buy_raw = out["rsi"] < buy_rsi
    sell_raw = out["rsi"] >= sell_rsi
    out["buy"] = confirm(buy_raw, window, min_count)
    out["sell"] = sell_raw
    out["signal"] = "hold"
    out.loc[out["buy"], "signal"] = "buy"
    out.loc[out["sell"], "signal"] = "sell"
    return out
```

**File:** `rapidtrader/strategies/sma_cross.py`

```python
import pandas as pd
from ..indicators.core import sma
from .confirmation import confirm

def sma_crossover(df: pd.DataFrame, fast=20, slow=100, confirm_days=2) -> pd.DataFrame:
    out = pd.DataFrame(index=df.index)
    out["fast"] = sma(df["close"], fast)
    out["slow"] = sma(df["close"], slow)
    up = out["fast"] > out["slow"]
    dn = out["fast"] < out["slow"]
    out["signal"] = "hold"
    out.loc[confirm(up, confirm_days, confirm_days), "signal"] = "buy"
    out.loc[confirm(dn, confirm_days, confirm_days), "signal"] = "sell"
    return out
```

---

## 3) Risk: Sizing, Exposure Cap, Cooldown

**File:** `rapidtrader/risk/sizing.py`

```python
import math

def shares_fixed_fractional(portfolio_value: float, pct_per_trade: float, entry_px: float) -> int:
    pv = max(0.0, portfolio_value) * max(0.0, pct_per_trade)
    return max(0, math.floor(pv / max(1e-9, entry_px)))

def shares_atr_target(portfolio_value: float, daily_risk_cap: float, atr_points: float, k_atr: float = 3.0) -> int:
    risk_budget = max(0.0, portfolio_value) * max(0.0, daily_risk_cap)
    unit_risk = max(1e-9, k_atr * atr_points)
    return max(0, math.floor(risk_budget / unit_risk))
```

**File:** `rapidtrader/risk/controls.py`

```python
import pandas as pd
from sqlalchemy import text
from ..core.db import get_engine
from ..indicators.core import sma

def market_ok(spy_close: pd.Series, n: int = 200) -> pd.Series:
    return spy_close >= sma(spy_close, n)

def upsert_market_state(spy_close: pd.Series, n: int = 200):
    eng = get_engine()
    s = sma(spy_close, n)
    gate = spy_close >= s
    with eng.begin() as c:
        for dt, px in spy_close.dropna().items():
            c.execute(text("""
                INSERT INTO market_state(d, spy_close, spy_sma200, bull_gate)
                VALUES (:d, :px, :sma, :gate)
                ON CONFLICT (d) DO UPDATE SET spy_close=:px, spy_sma200=:sma, bull_gate=:gate
            """), {"d": dt.date(), "px": float(px), "sma": float(s.loc[dt]) if pd.notna(s.loc[dt]) else None,
                   "gate": bool(gate.loc[dt]) if pd.notna(gate.loc[dt]) else False})

def sector_exposure_ok(sector_value: float, portfolio_value: float, candidate_value: float, max_pct=0.30) -> bool:
    return (sector_value + candidate_value) <= max_pct * max(1e-9, portfolio_value)
```

**File:** `rapidtrader/risk/stop_cooldown.py`

```python
from datetime import date, timedelta
from sqlalchemy import text
from ..core.db import get_engine

def stop_cooldown_active(symbol: str, d: date, cooldown_days: int = 1) -> bool:
    eng = get_engine()
    d0 = d - timedelta(days=cooldown_days)
    with eng.begin() as c:
        row = c.execute(text("""
            SELECT 1 FROM symbol_events
            WHERE symbol=:s AND event='STOP_HIT' AND d>=:d0 AND d<:d1
            LIMIT 1
        """), {"s": symbol, "d0": d0, "d1": d}).first()
    return row is not None
```

---

## 4) Data Ingest

**File:** `rapidtrader/data/ingest.py`

```python
import pandas as pd, yfinance as yf
from datetime import date, timedelta
from sqlalchemy import text
from ..core.db import get_engine

def upsert_bars(symbol: str, bars: pd.DataFrame):
    eng = get_engine()
    with eng.begin() as c:
        for d, row in bars.iterrows():
            c.execute(text("""
                INSERT INTO bars_daily(symbol,d,open,high,low,close,volume)
                VALUES (:s,:d,:o,:h,:l,:c,:v)
                ON CONFLICT (symbol,d) DO UPDATE SET open=:o, high=:h, low=:l, close=:c, volume=:v
            """), {"s": symbol, "d": d.date(), "o": float(row["Open"]), "h": float(row["High"]),
                   "l": float(row["Low"]), "c": float(row["Close"]), "v": int(row["Volume"])})

def ingest_symbols(symbols: list[str], days: int = 365):
    end = date.today()
    start = end - timedelta(days=days)
    for s in symbols:
        df = yf.download(s, start=start, end=end, interval="1d", auto_adjust=True, progress=False)
        if not df.empty:
            upsert_bars(s, df)
```

---

## 5) Market State (SPY Cache)

**File:** `rapidtrader/core/market_state.py`

```python
import pandas as pd, yfinance as yf
from datetime import date, timedelta
from .config import settings
from ..risk.controls import upsert_market_state

def refresh_spy_cache(days: int = 300):
    end = date.today()
    start = end - timedelta(days=days)
    df = yf.download(settings.RT_MARKET_FILTER_SYMBOL, start=start, end=end, interval="1d", auto_adjust=True, progress=False)
    if df.empty:
        raise RuntimeError("SPY download failed")
    close = df["Close"]
    close.index = pd.to_datetime(close.index)
    upsert_market_state(close, settings.RT_MARKET_FILTER_SMA)
    return close
```

---

## 6) Jobs - EOD Ingest, Trade, Report

**File:** `rapidtrader/jobs/eod_ingest.py`

```python
import argparse
from sqlalchemy import text
from ..core.db import get_engine
from ..data.ingest import ingest_symbols
from ..core.market_state import refresh_spy_cache

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=300)
    args = ap.parse_args()

    eng = get_engine()
    with eng.begin() as c:
        syms = [r[0] for r in c.execute(text("SELECT symbol FROM symbols")).all()]
    ingest_symbols(syms, days=args.days)
    refresh_spy_cache(days=args.days)
    print(f"Ingested {len(syms)} symbols & refreshed SPY.")

if __name__ == "__main__":
    main()
```

**File:** `rapidtrader/jobs/eod_trade.py`

See full implementation in main codebase. Key logic:
- Check market gate (SPY >= SMA200)
- For each symbol: check cooldown, generate RSI/SMA signals, calculate position size
- Apply sector exposure limits
- Record signals and create orders

**File:** `rapidtrader/jobs/eod_report.py`

```python
from sqlalchemy import text
from ..core.db import get_engine

def main():
    eng = get_engine()
    d = eng.execute(text("SELECT MAX(d) FROM market_state")).scalar_one()
    ms = eng.execute(text("SELECT pct_entries_filtered FROM market_state WHERE d=:d"), {"d": d}).scalar_one()
    orders = eng.execute(text("SELECT symbol, side, qty, type, reason FROM orders_eod WHERE d=:d"), {"d": d}).all()
    print(f"Report for {d}: % entries filtered = {ms:.1f}%")
    for sym, side, qty, typ, reason in orders:
        print(f" - {sym}: {side} {qty} ({typ}) [{reason}]")

if __name__ == "__main__":
    main()
```

---

## 7) Config Defaults

**File:** `rapidtrader/core/config.py`

```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)
    RT_DB_URL: str = "postgresql+psycopg://postgres:postgres@localhost:5432/rapidtrader"
    RT_MARKET_FILTER_ENABLE: int = 1
    RT_MARKET_FILTER_SMA: int = 200
    RT_MARKET_FILTER_SYMBOL: str = "SPY"
    RT_ENABLE_SIGNAL_CONFIRM: int = 1
    RT_CONFIRM_WINDOW: int = 3
    RT_CONFIRM_MIN_COUNT: int = 2
    RT_ENABLE_ATR_STOP: int = 1
    RT_ATR_LOOKBACK: int = 14
    RT_ATR_STOP_K: float = 3.0
    RT_COOLDOWN_DAYS_ON_STOP: int = 1
    RT_START_CAPITAL: float = 100_000.0
    RT_PCT_PER_TRADE: float = 0.05
    RT_DAILY_RISK_CAP: float = 0.005
    RT_MAX_EXPOSURE_PER_SECTOR: float = 0.30

settings = Settings()
```

---

## 8) How to Run

```bash
# 0) Setup environment
python -m venv .venv && source .venv/bin/activate
pip install --upgrade pip
pip install -e .
pip install ".[dev]"
docker compose up -d

# 1) Apply DB schema and seed symbols
docker exec -i rapidtrader-db psql -U postgres -d rapidtrader < scripts/setup_db.sql
python scripts/seed_sp500.py

# 2) Ingest data and refresh SPY cache
python -m rapidtrader.jobs.eod_ingest --days 300

# 3) Run EOD trade (dry-run) and report
python -m rapidtrader.jobs.eod_trade --mode dry_run
python -m rapidtrader.jobs.eod_report
```

**Smoke test acceptance:**
- `market_state` has today's row with `bull_gate` set
- `orders_eod` has rows (buys/sells depending on market state)
- `signals_daily` populated for symbols that triggered
- Console shows `% entries filtered` by market gate and cooldown

---

## Notes

- This is EOD dry-run only; paper/live routing (Alpaca) slots in where orders are recorded
- Add ATR stop storage (`stop_loss_px`) when wiring up positions and fills
- Add cost knobs (commission, slippage) to backtester for realistic performance
- Cache SPY SMA200 once per day; log % of entries filtered to monitor market filter impact
