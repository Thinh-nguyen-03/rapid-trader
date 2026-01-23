# Technical Trading Primer for RapidTrader

Essential technical analysis concepts and implementations used in the RapidTrader system.

## Overview

Technical analysis is the study of price and volume patterns to forecast future price movements. RapidTrader uses several key technical indicators to generate trading signals.

## Core Technical Indicators

### Simple Moving Average (SMA)

#### Definition
The Simple Moving Average is the arithmetic mean of closing prices over a specified number of periods.

#### Formula
```
SMA(n) = (P1 + P2 + ... + Pn) / n
```
Where:
- P1, P2, ..., Pn = Closing prices for the last n periods
- n = Number of periods (lookback window)

#### Implementation
```python
def sma(series: pd.Series, n: int) -> pd.Series:
    return series.rolling(window=n, min_periods=n).mean()
```

#### Trading Applications
- **Trend Identification**: Price above SMA = uptrend, below = downtrend
- **Support/Resistance**: SMA acts as dynamic support/resistance level
- **Crossover Signals**: Fast SMA crossing above/below slow SMA
- **Market Filter**: SPY above 200-day SMA = bull market

#### Common Periods
- **20-day SMA**: Short-term trend (1 month)
- **50-day SMA**: Medium-term trend (2.5 months)
- **200-day SMA**: Long-term trend (10 months)

### Relative Strength Index (RSI)

#### Definition
RSI measures the speed and magnitude of price changes to identify overbought and oversold conditions.

#### Formula (Wilder's Method)
```
RS = Average Gain / Average Loss
RSI = 100 - (100 / (1 + RS))

Average Gain = (Previous Average Gain × 13 + Current Gain) / 14
Average Loss = (Previous Average Loss × 13 + Current Loss) / 14
```

#### Implementation
```python
def rsi_wilder(close: pd.Series, window: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)

    avg_gain = gain.rolling(window=window, min_periods=window).mean()
    avg_loss = loss.rolling(window=window, min_periods=window).mean()

    for i in range(window, len(gain)):
        avg_gain.iloc[i] = (avg_gain.iloc[i-1] * (window-1) + gain.iloc[i]) / window
        avg_loss.iloc[i] = (avg_loss.iloc[i-1] * (window-1) + loss.iloc[i]) / window

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi
```

#### Trading Applications
- **Overbought**: RSI > 70 (consider selling)
- **Oversold**: RSI < 30 (consider buying)
- **Divergence**: Price makes new high/low but RSI doesn't confirm
- **Momentum**: Rising RSI = increasing momentum

#### Interpretation Levels
- **RSI > 80**: Extremely overbought
- **RSI 70-80**: Overbought zone
- **RSI 30-70**: Normal range
- **RSI 20-30**: Oversold zone
- **RSI < 20**: Extremely oversold

### Average True Range (ATR)

#### Definition
ATR measures market volatility by calculating the average of true ranges over a specified period.

#### Formula
```
True Range = MAX(
    High - Low,
    ABS(High - Previous Close),
    ABS(Low - Previous Close)
)

ATR = Average of True Range over n periods
```

#### Implementation
```python
def atr(high: pd.Series, low: pd.Series, close: pd.Series, n: int = 14) -> pd.Series:
    prev_close = close.shift(1)
    tr1 = high - low
    tr2 = abs(high - prev_close)
    tr3 = abs(low - prev_close)

    true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return true_range.rolling(window=n, min_periods=n).mean()
```

#### Trading Applications
- **Position Sizing**: Use ATR to determine position size based on volatility
- **Stop Losses**: Set stops at multiple of ATR (e.g., 3x ATR)
- **Volatility Filter**: Avoid trading during extremely low/high volatility
- **Breakout Confirmation**: High ATR confirms genuine breakouts

#### Volatility Interpretation
- **High ATR**: Increased volatility, wider stops needed
- **Low ATR**: Decreased volatility, tighter stops possible
- **Rising ATR**: Volatility expanding
- **Falling ATR**: Volatility contracting

## Trading Strategies

### RSI Mean-Reversion Strategy

#### Concept
Assumes prices revert to their mean after extreme moves. Uses RSI to identify oversold/overbought conditions.

#### Entry Rules
- **Buy Signal**: RSI < 30 (oversold condition)
- **Sell Signal**: RSI > 70 (overbought condition)
- **Confirmation**: Require 2 out of 3 consecutive days meeting criteria

#### Implementation
```python
def rsi_mean_reversion(df: pd.DataFrame, window: int = 3, min_count: int = 2) -> pd.DataFrame:
    rsi = rsi_wilder(df['close'])

    buy_raw = (rsi < 30).astype(int)
    sell_raw = (rsi > 70).astype(int)

    buy_confirmed = buy_raw.rolling(window=window).sum() >= min_count
    sell_confirmed = sell_raw.rolling(window=window).sum() >= min_count

    signals = pd.Series('hold', index=df.index)
    signals[buy_confirmed] = 'buy'
    signals[sell_confirmed] = 'sell'

    return pd.DataFrame({'signal': signals, 'rsi': rsi})
```

#### Risk Management
- **Stop Loss**: 3x ATR below entry price
- **Position Size**: Based on ATR volatility
- **Market Filter**: Only trade during bull markets (SPY > SMA200)

### SMA Crossover Strategy

#### Concept
Trend-following strategy based on the crossover of two moving averages of different periods.

#### Entry Rules
- **Buy Signal**: Fast SMA crosses above Slow SMA
- **Sell Signal**: Fast SMA crosses below Slow SMA
- **Common Combinations**: 20/50, 50/200

#### Implementation
```python
def sma_crossover(df: pd.DataFrame, fast: int = 20, slow: int = 50) -> pd.DataFrame:
    sma_fast = sma(df['close'], fast)
    sma_slow = sma(df['close'], slow)

    position = pd.Series(index=df.index, dtype=float)
    position[sma_fast > sma_slow] = 1
    position[sma_fast < sma_slow] = -1
    position = position.fillna(method='ffill').fillna(0)

    signals = pd.Series('hold', index=df.index)
    position_change = position.diff()
    signals[position_change > 0] = 'buy'
    signals[position_change < 0] = 'sell'

    return pd.DataFrame({
        'signal': signals,
        'sma_fast': sma_fast,
        'sma_slow': sma_slow,
        'position': position
    })
```

#### Advantages
- **Trend Following**: Captures sustained price movements
- **Objective**: Clear, rule-based entry/exit points
- **Versatile**: Works across different timeframes

#### Disadvantages
- **Whipsaws**: False signals during sideways markets
- **Lagging**: Signals come after trend has started
- **Drawdowns**: Can experience extended losing periods

## Signal Confirmation System

### 2-of-3 Confirmation

#### Concept
Reduces false signals by requiring multiple confirmations before acting on a signal.

#### Implementation
```python
def signal_confirmation(signals: pd.Series, window: int = 3, min_count: int = 2) -> pd.Series:
    buy_signals = (signals == 'buy').astype(int)
    sell_signals = (signals == 'sell').astype(int)

    buy_count = buy_signals.rolling(window=window).sum()
    sell_count = sell_signals.rolling(window=window).sum()

    confirmed_signals = pd.Series('hold', index=signals.index)
    confirmed_signals[buy_count >= min_count] = 'buy'
    confirmed_signals[sell_count >= min_count] = 'sell'

    return confirmed_signals
```

#### Benefits
- **Reduces Noise**: Filters out spurious signals
- **Improves Accuracy**: Higher probability of successful trades
- **Risk Reduction**: Fewer false breakouts and whipsaws

### Multi-Strategy Confirmation

#### Concept
Combine signals from multiple strategies to increase confidence.

#### Implementation
```python
def multi_strategy_confirmation(rsi_signals: pd.Series, sma_signals: pd.Series) -> pd.DataFrame:
    signal_scores = pd.DataFrame({
        'rsi_score': (rsi_signals == 'buy').astype(int) - (rsi_signals == 'sell').astype(int),
        'sma_score': (sma_signals == 'buy').astype(int) - (sma_signals == 'sell').astype(int)
    })

    combined_score = signal_scores.sum(axis=1)

    final_signals = pd.Series('hold', index=rsi_signals.index)
    final_signals[combined_score >= 1] = 'buy'
    final_signals[combined_score <= -1] = 'sell'

    return pd.DataFrame({
        'signal': final_signals,
        'score': combined_score,
        'rsi_signal': rsi_signals,
        'sma_signal': sma_signals
    })
```

## Risk Management Applications

### Position Sizing with ATR

#### Concept
Use ATR to determine appropriate position size based on volatility.

#### Implementation
```python
def atr_position_size(portfolio_value: float, risk_per_trade: float,
                     entry_price: float, atr_value: float, atr_multiplier: float = 3.0) -> int:
    risk_per_share = atr_value * atr_multiplier
    total_risk = portfolio_value * risk_per_trade
    shares = int(total_risk / risk_per_share)
    max_shares = int(portfolio_value / entry_price)
    return min(shares, max_shares)
```

### Market Regime Filter

#### Concept
Use SPY's position relative to its 200-day SMA to determine market regime.

#### Implementation
```python
def market_regime_filter(spy_price: float, spy_sma200: float) -> str:
    if spy_price > spy_sma200:
        return 'bull'
    else:
        return 'bear'
```

#### Application
- **Bull Market**: SPY > SMA200, allow new long positions
- **Bear Market**: SPY < SMA200, avoid new long positions
- **Regime Change**: Alert when market regime changes

## Best Practices

### Indicator Selection
1. **Complementary Indicators**: Use indicators that measure different aspects (trend, momentum, volatility)
2. **Parameter Optimization**: Test different periods to find optimal settings
3. **Market Adaptation**: Adjust parameters for different market conditions
4. **Simplicity**: Start with simple, well-understood indicators

### Signal Generation
1. **Clear Rules**: Define precise entry/exit criteria
2. **Confirmation**: Use multiple confirmations to reduce false signals
3. **Time Consistency**: Apply consistent timeframes across analysis
4. **Backtesting**: Test strategies on historical data before deployment

### Risk Management
1. **Position Sizing**: Never risk more than predetermined amount per trade
2. **Stop Losses**: Always define exit point before entering trade
3. **Diversification**: Spread risk across multiple positions and sectors
4. **Market Conditions**: Adjust strategy based on market regime

### Common Pitfalls
1. **Curve Fitting**: Over-optimizing parameters to historical data
2. **Late Signals**: Acting on lagging indicators without confirmation
3. **Ignoring Risk**: Focusing on returns without considering risk
4. **Emotional Override**: Deviating from systematic rules based on feelings

## Advanced Concepts

### Multi-Timeframe Analysis
- **Higher Timeframe Trend**: Use daily/weekly charts for overall direction
- **Lower Timeframe Entry**: Use hourly charts for precise entry points
- **Alignment**: Trade only when multiple timeframes agree

### Volatility Regimes
- **Low Volatility**: Expect breakouts and trend changes
- **High Volatility**: Expect mean reversion and range-bound trading
- **Volatility Clustering**: High volatility periods tend to cluster

### Market Microstructure
- **Volume Analysis**: Confirm price moves with volume
- **Time of Day**: Consider intraday patterns (opening gaps, closing effects)
- **Day of Week**: Be aware of calendar effects (Monday blues, Friday rallies)

## Performance Measurement

### Key Metrics
1. **Win Rate**: Percentage of profitable trades
2. **Risk-Reward Ratio**: Average win divided by average loss
3. **Profit Factor**: Gross profit divided by gross loss
4. **Maximum Drawdown**: Largest peak-to-trough decline
5. **Sharpe Ratio**: Risk-adjusted return measure

### Continuous Improvement
1. **Regular Review**: Analyze strategy performance monthly
2. **Parameter Adjustment**: Fine-tune based on market conditions
3. **New Strategies**: Research and test additional approaches
4. **Risk Assessment**: Monitor and adjust risk parameters

This primer provides the foundation for understanding the technical analysis concepts used in RapidTrader. For deeper study, consider reading classic texts like "Technical Analysis of the Financial Markets" by John Murphy or "New Concepts in Technical Trading Systems" by J. Welles Wilder Jr.
