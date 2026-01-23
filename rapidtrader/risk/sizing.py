"""Position sizing algorithms for RapidTrader."""

import math


def shares_fixed_fractional(
    portfolio_value: float,
    pct_per_trade: float,
    entry_px: float
) -> int:
    """Calculate position size using fixed-fractional method.

    Args:
        portfolio_value: Total portfolio value in dollars
        pct_per_trade: Percentage of portfolio per trade (e.g., 0.05 = 5%)
        entry_px: Expected entry price per share

    Returns:
        Number of shares to purchase (integer)
    """
    portfolio_value = max(0.0, portfolio_value)
    pct_per_trade = max(0.0, pct_per_trade)
    entry_px = max(1e-9, entry_px)

    position_value = portfolio_value * pct_per_trade
    shares = math.floor(position_value / entry_px)

    return max(0, shares)


def shares_atr_target(
    portfolio_value: float,
    daily_risk_cap: float,
    atr_points: float,
    k_atr: float = 3.0
) -> int:
    """Calculate position size using ATR-based volatility targeting.

    Args:
        portfolio_value: Total portfolio value in dollars
        daily_risk_cap: Maximum daily risk as fraction of portfolio (e.g., 0.005 = 0.5%)
        atr_points: Average True Range in price points
        k_atr: ATR multiplier for stop distance (default 3.0)

    Returns:
        Number of shares to purchase (integer)
    """
    portfolio_value = max(0.0, portfolio_value)
    daily_risk_cap = max(0.0, daily_risk_cap)
    atr_points = max(1e-9, atr_points)
    k_atr = max(0.0, k_atr)

    risk_budget = portfolio_value * daily_risk_cap
    unit_risk = k_atr * atr_points
    shares = math.floor(risk_budget / unit_risk)

    return max(0, shares)


def apply_vix_scaling(shares: int, vix_multiplier: float) -> int:
    """Apply VIX-based scaling to position size.

    Args:
        shares: Original number of shares
        vix_multiplier: VIX scale factor (0.0 to 1.0)

    Returns:
        Adjusted number of shares
    """
    if vix_multiplier <= 0:
        return 0
    if vix_multiplier >= 1.0:
        return shares

    return max(0, int(shares * vix_multiplier))


def compute_position_size(
    portfolio_value: float,
    entry_px: float,
    atr_points: float,
    pct_per_trade: float = 0.05,
    daily_risk_cap: float = 0.005,
    k_atr: float = 3.0,
    vix_multiplier: float = 1.0
) -> int:
    """Compute final position size using all sizing methods and scaling.

    Takes the minimum of fixed-fractional and ATR-target sizing,
    then applies VIX scaling.

    Args:
        portfolio_value: Total portfolio value in dollars
        entry_px: Expected entry price per share
        atr_points: Average True Range in price points
        pct_per_trade: Percentage of portfolio per trade (default 0.05)
        daily_risk_cap: Maximum daily risk as fraction (default 0.005)
        k_atr: ATR multiplier for stop distance (default 3.0)
        vix_multiplier: VIX-based scale factor (default 1.0)

    Returns:
        Final number of shares to purchase
    """
    qty_ff = shares_fixed_fractional(portfolio_value, pct_per_trade, entry_px)
    qty_atr = shares_atr_target(portfolio_value, daily_risk_cap, atr_points, k_atr)

    base_qty = min(qty_ff, qty_atr)

    return apply_vix_scaling(base_qty, vix_multiplier)
