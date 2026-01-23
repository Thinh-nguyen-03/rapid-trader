"""Risk control mechanisms for RapidTrader.

Implements various risk controls:
1. Market filter using SPY 200-SMA bull/bear detection
2. Sector exposure limits
3. Portfolio heat limit (total ATR-based risk)
4. VIX-based position scaling
5. Correlation check for new positions
6. Market state caching for performance
"""

import numpy as np
import pandas as pd
from datetime import date, timedelta
from sqlalchemy import text
from ..core.db import get_engine
from ..indicators.core import sma


def market_ok(spy_close: pd.Series, n: int = 200) -> pd.Series:
    """Determine if market conditions are favorable for new entries.
    
    Args:
        spy_close: SPY closing prices as pandas Series
        n: SMA period for market filter (default 200)
        
    Returns:
        Boolean series where True indicates bullish market (SPY >= SMA200)
        
    Market Filter Logic:
        - Bull market: SPY closing price >= 200-day SMA
        - Bear market: SPY closing price < 200-day SMA
        - No new long entries during bear markets
    """
    spy_sma = sma(spy_close, n)
    return spy_close >= spy_sma


def upsert_market_state(spy_close: pd.Series, n: int = 200):
    """Update market state cache in database.
    
    Args:
        spy_close: SPY closing prices as pandas Series
        n: SMA period for calculation (default 200)
        
    Updates market_state table with:
        - spy_close: SPY closing price
        - spy_sma200: 200-day SMA value
        - bull_gate: Boolean indicating bullish market
    """
    eng = get_engine()
    spy_sma = sma(spy_close, n)
    bull_gate = market_ok(spy_close, n)
    
    with eng.begin() as conn:
        for dt, close_px in spy_close.dropna().items():
            sma_val = spy_sma.loc[dt] if pd.notna(spy_sma.loc[dt]) else None
            gate_val = bool(bull_gate.loc[dt]) if pd.notna(bull_gate.loc[dt]) else False
            
            conn.execute(text("""
                INSERT INTO market_state (d, spy_close, spy_sma200, bull_gate)
                VALUES (:d, :px, :sma, :gate)
                ON CONFLICT (d) DO UPDATE SET 
                    spy_close = :px, 
                    spy_sma200 = :sma, 
                    bull_gate = :gate
            """), {
                "d": dt.date(), 
                "px": float(close_px), 
                "sma": float(sma_val) if sma_val is not None else None,
                "gate": gate_val
            })


def sector_exposure_ok(
    current_sector_value: float, 
    portfolio_value: float, 
    candidate_value: float, 
    max_pct: float = 0.30
) -> bool:
    """Check if adding a position would violate sector exposure limits.
    
    Args:
        current_sector_value: Current dollar value invested in this sector
        portfolio_value: Total portfolio value
        candidate_value: Dollar value of proposed new position
        max_pct: Maximum sector exposure as fraction (default 0.30 = 30%)
        
    Returns:
        True if the new position would keep sector exposure within limits
        
    Examples:
        >>> sector_exposure_ok(25000, 100000, 10000, 0.30)
        False  # (25k + 10k) / 100k = 35% > 30% limit
        
        >>> sector_exposure_ok(20000, 100000, 5000, 0.30) 
        True   # (20k + 5k) / 100k = 25% < 30% limit
    """
    # Avoid division by zero
    portfolio_value = max(1e-9, portfolio_value)
    
    # Calculate total sector exposure after adding candidate position
    total_sector_value = current_sector_value + candidate_value
    sector_exposure_pct = total_sector_value / portfolio_value
    
    return sector_exposure_pct <= max_pct


def portfolio_heat_ok(
    positions: list[dict],
    atr_values: dict[str, float],
    portfolio_value: float,
    max_heat_pct: float = 0.06
) -> tuple[bool, float]:
    """Check if total portfolio risk (heat) is within acceptable limits.

    Args:
        positions: List of position dicts with 'symbol' and 'qty' keys
        atr_values: Dict mapping symbol to current ATR value
        portfolio_value: Current portfolio value
        max_heat_pct: Maximum allowed heat as fraction of portfolio (default 6%)

    Returns:
        Tuple of (is_ok, current_heat_pct)
    """
    portfolio_value = max(1e-9, portfolio_value)

    total_risk = sum(
        abs(pos.get('qty', 0)) * atr_values.get(pos.get('symbol', ''), 0)
        for pos in positions
    )

    current_heat = total_risk / portfolio_value
    return current_heat < max_heat_pct, current_heat


def get_current_positions() -> list[dict]:
    """Get current positions from database.

    Returns:
        List of position dicts with symbol, qty, avg_px, sector
    """
    eng = get_engine()

    with eng.begin() as conn:
        result = conn.execute(text("""
            SELECT symbol, qty, avg_px, sector
            FROM positions
            WHERE qty > 0
        """)).all()

    return [
        {"symbol": row[0], "qty": row[1], "avg_px": row[2], "sector": row[3]}
        for row in result
    ]


def get_position_atr_values(symbols: list[str], lookback: int = 14) -> dict[str, float]:
    """Get ATR values for a list of symbols.

    Args:
        symbols: List of symbols to get ATR for
        lookback: ATR calculation period

    Returns:
        Dict mapping symbol to ATR value
    """
    if not symbols:
        return {}

    eng = get_engine()
    from ..indicators.core import atr

    atr_values = {}
    for symbol in symbols:
        query = text("""
            SELECT d, high, low, close FROM bars_daily
            WHERE symbol = :symbol
            ORDER BY d DESC
            LIMIT :limit
        """)

        df = pd.read_sql(
            query, eng,
            params={"symbol": symbol, "limit": lookback + 5},
            parse_dates=["d"]
        ).sort_values("d")

        if len(df) >= lookback:
            atr_series = atr(df["high"], df["low"], df["close"], lookback)
            if not atr_series.empty and pd.notna(atr_series.iloc[-1]):
                atr_values[symbol] = float(atr_series.iloc[-1])

    return atr_values


def vix_scale_factor(vix: float, threshold_elevated: float = 20.0,
                     threshold_high: float = 30.0,
                     scale_elevated: float = 0.5,
                     scale_high: float = 0.25) -> float:
    """Calculate position size multiplier based on VIX level.

    Args:
        vix: Current VIX value
        threshold_elevated: VIX level for elevated fear (default 20)
        threshold_high: VIX level for high fear (default 30)
        scale_elevated: Size multiplier when elevated (default 0.5)
        scale_high: Size multiplier when high (default 0.25)

    Returns:
        Position size multiplier (0.0 to 1.0)
    """
    if vix >= threshold_high:
        return scale_high
    elif vix >= threshold_elevated:
        return scale_elevated
    else:
        return 1.0


def get_current_vix() -> float | None:
    """Get current VIX value from database.

    Returns:
        Current VIX close price, or None if not available
    """
    eng = get_engine()

    # Try to get VIX from bars_daily (symbol: VIX or ^VIX)
    with eng.begin() as conn:
        result = conn.execute(text("""
            SELECT close FROM bars_daily
            WHERE symbol IN ('VIX', '^VIX', 'VIXY')
            ORDER BY d DESC
            LIMIT 1
        """)).first()

    if result:
        return float(result[0])

    return None


def correlation_ok(
    symbol: str,
    existing_positions: list[dict],
    threshold: float = 0.75,
    lookback: int = 60,
    top_n: int = 3
) -> tuple[bool, str | None]:
    """Check if a new symbol is acceptably uncorrelated with existing positions.

    Args:
        symbol: Symbol to check
        existing_positions: List of position dicts with 'symbol' and 'value' keys
        threshold: Max allowed correlation (default 0.75)
        lookback: Days of returns to use (default 60)
        top_n: Number of largest positions to check against (default 3)

    Returns:
        (True, None) if correlation is acceptable
        (False, correlated_symbol) if correlation exceeds threshold
    """
    if not existing_positions:
        return True, None

    eng = get_engine()

    # Sort by position value, take top N
    sorted_positions = sorted(
        existing_positions,
        key=lambda x: abs(x.get('qty', 0) * x.get('avg_px', 0)),
        reverse=True
    )[:top_n]

    if not sorted_positions:
        return True, None

    # Get symbols to check
    position_symbols = [p['symbol'] for p in sorted_positions if p.get('symbol')]
    all_symbols = [symbol] + position_symbols

    # Fetch returns data for all symbols
    cutoff_date = date.today() - timedelta(days=lookback + 10)

    query = text("""
        SELECT symbol, d, close FROM bars_daily
        WHERE symbol = ANY(:symbols) AND d >= :cutoff
        ORDER BY symbol, d
    """)

    df = pd.read_sql(
        query, eng,
        params={"symbols": all_symbols, "cutoff": cutoff_date},
        parse_dates=["d"]
    )

    if df.empty:
        return True, None

    # Pivot to get prices per symbol
    prices = df.pivot(index='d', columns='symbol', values='close')

    if symbol not in prices.columns:
        return True, None

    # Calculate returns
    returns = prices.pct_change().dropna()

    if len(returns) < 20:  # Need minimum data
        return True, None

    symbol_returns = returns[symbol].tail(lookback)

    # Check correlation with each position
    for pos in sorted_positions:
        pos_symbol = pos.get('symbol')
        if not pos_symbol or pos_symbol not in returns.columns:
            continue

        pos_returns = returns[pos_symbol].tail(lookback)

        # Calculate correlation
        if len(symbol_returns) > 0 and len(pos_returns) > 0:
            corr = symbol_returns.corr(pos_returns)
            if pd.notna(corr) and corr > threshold:
                return False, pos_symbol

    return True, None
