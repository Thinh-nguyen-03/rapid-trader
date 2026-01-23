# RapidTrader: Signals & Position Sizing Reference

This document provides a complete technical reference for all signal generation and position sizing logic used in RapidTrader.

---

## Table of Contents

1. [Technical Indicators](#1-technical-indicators)
2. [Signal Confirmation Logic](#2-signal-confirmation-logic)
3. [Trading Strategies](#3-trading-strategies)
4. [Position Sizing](#4-position-sizing)
5. [Risk Controls](#5-risk-controls)
6. [Signal Flow Summary](#6-signal-flow-summary)

---

## 1. Technical Indicators

**Source:** `rapidtrader/indicators/core.py`

### 1.1 Simple Moving Average (SMA)

```python
def sma(series: pd.Series, n: int) -> pd.Series:
    """Simple Moving Average"""
    return series.rolling(n, min_periods=n).mean()
```

**Math:**

$$
SMA_n = \frac{1}{n} \sum_{i=0}^{n-1} P_{t-i}
$$

Where:
- $P_t$ = Price at time $t$
- $n$ = Lookback period

---

### 1.2 RSI (Wilder's Smoothing)

```python
def rsi_wilder(close: pd.Series, window: int = 14) -> pd.Series:
    """RSI with Wilder's smoothing (EMA-based)"""
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1/window, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/window, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, pd.NA)
    return 100 - (100 / (1 + rs))
```

**Math:**

1. **Price Change:**
   $$\Delta P_t = P_t - P_{t-1}$$

2. **Gains and Losses:**
   $$Gain_t = \max(\Delta P_t, 0)$$
   $$Loss_t = \max(-\Delta P_t, 0)$$

3. **Wilder's Exponential Moving Average:**
   $$AvgGain_t = \alpha \cdot Gain_t + (1 - \alpha) \cdot AvgGain_{t-1}$$
   $$AvgLoss_t = \alpha \cdot Loss_t + (1 - \alpha) \cdot AvgLoss_{t-1}$$

   Where $\alpha = \frac{1}{window}$ (default: $\frac{1}{14}$)

4. **Relative Strength:**
   $$RS = \frac{AvgGain}{AvgLoss}$$

5. **RSI Formula:**
   $$RSI = 100 - \frac{100}{1 + RS}$$

**Interpretation:**
- RSI > 70: Overbought
- RSI < 30: Oversold
- RSI oscillates between 0 and 100

---

### 1.3 Average True Range (ATR)

```python
def atr(high: pd.Series, low: pd.Series, close: pd.Series, n: int = 14) -> pd.Series:
    """Average True Range using Wilder's smoothing"""
    prev_close = close.shift(1)
    tr = pd.concat([
        (high - low),
        (high - prev_close).abs(),
        (low - prev_close).abs()
    ], axis=1).max(axis=1)
    return tr.ewm(alpha=1/n, adjust=False, min_periods=n).mean()
```

**Math:**

1. **True Range (TR):**
   $$TR_t = \max\Big[(H_t - L_t),\ |H_t - C_{t-1}|,\ |L_t - C_{t-1}|\Big]$$

   Where:
   - $H_t$ = High price
   - $L_t$ = Low price
   - $C_{t-1}$ = Previous close

2. **ATR (Wilder's EMA):**
   $$ATR_t = \alpha \cdot TR_t + (1 - \alpha) \cdot ATR_{t-1}$$

   Where $\alpha = \frac{1}{n}$ (default: $\frac{1}{14}$)

**Use Case:** Measures volatility in price points; used for position sizing and stop-loss placement.

---

## 2. Signal Confirmation Logic

**Source:** `rapidtrader/strategies/confirmation.py`

### 2.1 Confirmation Filter

```python
def confirm(signal_bool: pd.Series, window: int, min_count: int) -> pd.Series:
    """Apply confirmation logic to a boolean signal series.

    Args:
        signal_bool: Boolean series of raw signals (True = signal present)
        window: Number of periods to look back for confirmation
        min_count: Minimum number of confirmations required in window

    Returns:
        Boolean series where True indicates confirmed signal
    """
    # Convert boolean to integer (True=1, False=0)
    signal_int = signal_bool.astype(int)

    # Calculate rolling sum of signals
    strength = signal_int.rolling(window, min_periods=1).sum()

    # Return True where strength meets minimum threshold
    return strength >= min_count
```

**Math:**

$$
Confirmed_t = \begin{cases}
True & \text{if } \sum_{i=0}^{window-1} Signal_{t-i} \geq min\_count \\
False & \text{otherwise}
\end{cases}
$$

**Example (2-of-3 confirmation):**

| Day | Raw Signal | Rolling Sum (3-day) | Confirmed |
|-----|------------|---------------------|-----------|
| 1   | True       | 1                   | False     |
| 2   | True       | 2                   | **True**  |
| 3   | False      | 2                   | **True**  |
| 4   | True       | 2                   | **True**  |
| 5   | False      | 1                   | False     |

**Purpose:** Reduces whipsaws and false signals by requiring persistence.

---

## 3. Trading Strategies

### 3.1 SMA Crossover Strategy

**Source:** `rapidtrader/strategies/sma_cross.py`

```python
def sma_crossover(
    df: pd.DataFrame,
    fast: int = 20,
    slow: int = 100,
    confirm_days: int = 2
) -> pd.DataFrame:
    """Generate SMA crossover signals with confirmation."""
    out = pd.DataFrame(index=df.index)

    # Calculate moving averages
    out["fast"] = sma(df["close"], fast)
    out["slow"] = sma(df["close"], slow)

    # Generate raw crossover signals
    up_trend = out["fast"] > out["slow"]    # Fast above slow = bullish
    down_trend = out["fast"] < out["slow"]  # Fast below slow = bearish

    # Apply confirmation logic
    confirmed_up = confirm(up_trend, confirm_days, confirm_days)
    confirmed_down = confirm(down_trend, confirm_days, confirm_days)

    # Generate final signals
    out["signal"] = "hold"
    out.loc[confirmed_up, "signal"] = "buy"
    out.loc[confirmed_down, "signal"] = "sell"

    return out
```

**Parameters:**
| Parameter | Default | Description |
|-----------|---------|-------------|
| `fast` | 20 | Fast SMA period |
| `slow` | 100 | Slow SMA period |
| `confirm_days` | 2 | Consecutive days required for confirmation |

**Signal Logic:**

```
BUY:  SMA_fast > SMA_slow  (for confirm_days consecutive days)
SELL: SMA_fast < SMA_slow  (for confirm_days consecutive days)
HOLD: Otherwise
```

**Visual Representation:**

```
Price
  ^
  |    ___/\___
  |   /        \___  <- Price
  |  /    ____
  | /    /    \___   <- Fast SMA (20)
  |/____/
  |_______________   <- Slow SMA (100)
  |
  +-------------------> Time
       ^         ^
       BUY      SELL
    (crossover) (crossunder)
```

---

### 3.2 RSI Mean-Reversion Strategy

**Source:** `rapidtrader/strategies/rsi_mr.py`

```python
def rsi_mean_reversion(
    df: pd.DataFrame,
    buy_rsi: float = 30.0,
    sell_rsi: float = 55.0,
    window: int = 3,
    min_count: int = 2
) -> pd.DataFrame:
    """Generate RSI mean-reversion signals with confirmation."""
    out = pd.DataFrame(index=df.index)

    # Calculate RSI using Wilder's method (14-period default)
    out["rsi"] = rsi_wilder(df["close"], window=14)

    # Generate raw signals
    buy_raw = out["rsi"] < buy_rsi
    sell_raw = out["rsi"] >= sell_rsi

    # Apply confirmation to buy signals only
    # Exits (sells) don't need confirmation for faster risk management
    out["buy"] = confirm(buy_raw, window, min_count)
    out["sell"] = sell_raw

    # Determine final signal with priority: sell > buy > hold
    out["signal"] = "hold"
    out.loc[out["buy"], "signal"] = "buy"
    out.loc[out["sell"], "signal"] = "sell"  # Sells override buys

    return out
```

**Parameters:**
| Parameter | Default | Description |
|-----------|---------|-------------|
| `buy_rsi` | 30.0 | RSI threshold for oversold (buy) |
| `sell_rsi` | 55.0 | RSI threshold for exit (sell) |
| `window` | 3 | Confirmation window size |
| `min_count` | 2 | Minimum confirmations (2-of-3) |

**Signal Logic:**

```
BUY:  RSI < 30 (confirmed: 2 of last 3 days)
SELL: RSI >= 55 (immediate, no confirmation)
HOLD: Otherwise

Priority: SELL > BUY > HOLD
```

**Rationale:**
- **Buy confirmation (2-of-3):** Prevents catching falling knives; ensures oversold condition persists
- **Immediate sell:** Faster exits protect capital; no waiting when exit conditions are met

**RSI Zones:**

```
RSI
100 |
 80 |  ////////////////  <- Overbought zone (not used)
 70 |------------------
    |
 55 |------ SELL ------  <- Exit threshold
    |
 30 |------ BUY -------  <- Entry threshold (with confirmation)
 20 |  \\\\\\\\\\\\\\\\  <- Oversold zone
  0 |
```

---

## 4. Position Sizing

**Source:** `rapidtrader/risk/sizing.py`

### 4.1 Fixed-Fractional Sizing

```python
def shares_fixed_fractional(
    portfolio_value: float,
    pct_per_trade: float,
    entry_px: float
) -> int:
    """Calculate position size using fixed-fractional method."""
    portfolio_value = max(0.0, portfolio_value)
    pct_per_trade = max(0.0, pct_per_trade)
    entry_px = max(1e-9, entry_px)

    position_value = portfolio_value * pct_per_trade
    shares = math.floor(position_value / entry_px)

    return max(0, shares)
```

**Math:**

$$
Shares = \left\lfloor \frac{PortfolioValue \times PctPerTrade}{EntryPrice} \right\rfloor
$$

**Example:**
```
Portfolio:   $100,000
Risk/Trade:  5% (0.05)
Entry Price: $50.00

Position Value = $100,000 × 0.05 = $5,000
Shares = floor($5,000 / $50) = 100 shares
```

**Characteristics:**
- Simple and predictable
- Position size scales with portfolio
- Does not account for volatility

---

### 4.2 ATR-Target Sizing (Volatility-Based)

```python
def shares_atr_target(
    portfolio_value: float,
    daily_risk_cap: float,
    atr_points: float,
    k_atr: float = 3.0
) -> int:
    """Calculate position size using ATR-based volatility targeting."""
    portfolio_value = max(0.0, portfolio_value)
    daily_risk_cap = max(0.0, daily_risk_cap)
    atr_points = max(1e-9, atr_points)
    k_atr = max(0.0, k_atr)

    risk_budget = portfolio_value * daily_risk_cap
    unit_risk = k_atr * atr_points
    shares = math.floor(risk_budget / unit_risk)

    return max(0, shares)
```

**Math:**

$$
RiskBudget = PortfolioValue \times DailyRiskCap
$$

$$
UnitRisk = k_{ATR} \times ATR
$$

$$
Shares = \left\lfloor \frac{RiskBudget}{UnitRisk} \right\rfloor
$$

**Example:**
```
Portfolio:      $100,000
Daily Risk Cap: 0.5% (0.005)
ATR:            $2.00
k_ATR:          3.0 (stop at 3× ATR)

Risk Budget = $100,000 × 0.005 = $500
Unit Risk   = 3.0 × $2.00 = $6.00 per share
Shares      = floor($500 / $6.00) = 83 shares
```

**Intuition:**
- Assumes stop-loss is placed at $k_{ATR} \times ATR$ away from entry
- Sizes position so that if stopped out, loss = daily risk cap
- **Higher volatility → Smaller position**
- **Lower volatility → Larger position**

---

### 4.3 Combined Sizing (Production Use)

In production (`eod_trade.py`), both methods are calculated and the **minimum** is used:

```python
qty = min(
    shares_fixed_fractional(portfolio_value, 0.05, entry_px),
    shares_atr_target(portfolio_value, 0.005, atr_val, 3.0)
)
```

**Rationale:**
- Fixed-fractional provides a ceiling on position size
- ATR-target reduces size in volatile conditions
- Taking the minimum ensures conservative sizing

---

## 5. Risk Controls

**Source:** `rapidtrader/risk/controls.py`

### 5.1 Market Filter (SPY 200-SMA)

```python
def market_ok(spy_close: pd.Series, n: int = 200) -> pd.Series:
    """Determine if market conditions are favorable for new entries."""
    spy_sma = sma(spy_close, n)
    return spy_close >= spy_sma
```

**Logic:**

$$
MarketOK = \begin{cases}
True & \text{if } SPY_{close} \geq SMA_{200}(SPY) \\
False & \text{otherwise}
\end{cases}
$$

**Application:**
- **Bull Market (True):** Allow new long entries
- **Bear Market (False):** Block new long entries (existing positions can be held/sold)

**Visual:**
```
SPY
  ^
  |   /\    /\      /\
  |  /  \  /  \    /  \    <- SPY Price
  | /    \/    \  /    \
  |____________\_/______   <- 200-SMA
  |      ^           ^
  |    BEAR        BULL
  +-----------------------> Time
```

---

### 5.2 Sector Exposure Limit

```python
def sector_exposure_ok(
    current_sector_value: float,
    portfolio_value: float,
    candidate_value: float,
    max_pct: float = 0.30
) -> bool:
    """Check if adding a position would violate sector exposure limits."""
    portfolio_value = max(1e-9, portfolio_value)
    total_sector_value = current_sector_value + candidate_value
    sector_exposure_pct = total_sector_value / portfolio_value
    return sector_exposure_pct <= max_pct
```

**Math:**

$$
SectorExposure = \frac{CurrentSectorValue + CandidateValue}{PortfolioValue}
$$

$$
Allowed = SectorExposure \leq MaxPct
$$

**Example:**
```
Portfolio:         $100,000
Current in Tech:   $25,000
Proposed Trade:    $10,000 (Tech stock)
Max Sector:        30%

New Exposure = ($25,000 + $10,000) / $100,000 = 35%
Result: BLOCKED (35% > 30% limit)
```

**Purpose:** Prevents concentration risk in any single sector.

---

## 6. Signal Flow Summary

### End-to-End Process

```
┌─────────────────────────────────────────────────────────────┐
│                    DATA ACQUISITION                         │
│  Load 250 bars of OHLCV data for each symbol               │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   SIGNAL GENERATION                         │
│                                                             │
│  ┌─────────────────┐      ┌─────────────────┐              │
│  │  RSI Strategy   │      │  SMA Strategy   │              │
│  │  (rsi_mr.py)    │      │  (sma_cross.py) │              │
│  │                 │      │                 │              │
│  │ RSI < 30 → BUY  │      │ Fast > Slow     │              │
│  │ RSI ≥ 55 → SELL │      │   → BUY         │              │
│  └────────┬────────┘      └────────┬────────┘              │
│           │                        │                        │
│           └──────────┬─────────────┘                        │
│                      ▼                                      │
│           ┌─────────────────────┐                          │
│           │  Signal Priority    │                          │
│           │  SELL > BUY > HOLD  │                          │
│           └─────────────────────┘                          │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   RISK FILTERS                              │
│                                                             │
│  ┌─────────────────┐      ┌─────────────────┐              │
│  │  Market Filter  │      │ Sector Exposure │              │
│  │  SPY ≥ SMA200   │      │    ≤ 30%        │              │
│  └─────────────────┘      └─────────────────┘              │
│                                                             │
│  If filters fail → Signal blocked                          │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                  POSITION SIZING                            │
│                                                             │
│  ┌─────────────────┐      ┌─────────────────┐              │
│  │ Fixed-Fractional│      │   ATR-Target    │              │
│  │   (5% max)      │      │  (0.5% risk)    │              │
│  └────────┬────────┘      └────────┬────────┘              │
│           │                        │                        │
│           └──────────┬─────────────┘                        │
│                      ▼                                      │
│           ┌─────────────────────┐                          │
│           │  Take MINIMUM of    │                          │
│           │  both methods       │                          │
│           └─────────────────────┘                          │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   ORDER CREATION                            │
│                                                             │
│  Record to signals_daily table                             │
│  Create order in orders_eod table                          │
│  (Symbol, Side, Quantity, Reason)                          │
└─────────────────────────────────────────────────────────────┘
```

### Default Parameters Summary

| Component | Parameter | Default | Description |
|-----------|-----------|---------|-------------|
| **RSI** | window | 14 | RSI calculation period |
| **RSI Strategy** | buy_rsi | 30 | Oversold threshold |
| **RSI Strategy** | sell_rsi | 55 | Exit threshold |
| **RSI Strategy** | confirmation | 2-of-3 | Buy signal confirmation |
| **SMA Strategy** | fast | 20 | Fast SMA period |
| **SMA Strategy** | slow | 100 | Slow SMA period |
| **SMA Strategy** | confirm_days | 2 | Crossover confirmation |
| **Market Filter** | n | 200 | SPY SMA period |
| **Sector Limit** | max_pct | 30% | Max sector exposure |
| **Fixed-Fractional** | pct_per_trade | 5% | Position size cap |
| **ATR-Target** | daily_risk_cap | 0.5% | Daily risk limit |
| **ATR-Target** | k_atr | 3.0 | Stop-loss multiplier |

---

## File Reference

| Module | Path | Purpose |
|--------|------|---------|
| Indicators | `rapidtrader/indicators/core.py` | SMA, RSI, ATR calculations |
| Confirmation | `rapidtrader/strategies/confirmation.py` | Signal confirmation filter |
| SMA Strategy | `rapidtrader/strategies/sma_cross.py` | SMA crossover signals |
| RSI Strategy | `rapidtrader/strategies/rsi_mr.py` | RSI mean-reversion signals |
| Sizing | `rapidtrader/risk/sizing.py` | Position sizing algorithms |
| Controls | `rapidtrader/risk/controls.py` | Market filter, sector limits |
| Orchestration | `rapidtrader/jobs/eod_trade.py` | End-of-day job execution |
