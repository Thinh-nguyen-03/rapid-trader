"""Position sizing algorithms for RapidTrader.

Implements multiple position sizing methods:
1. Fixed-fractional sizing: Fixed percentage of portfolio per trade
2. ATR-target sizing: Size based on volatility and daily risk limit
"""

import math


def shares_fixed_fractional(
    portfolio_value: float, 
    pct_per_trade: float, 
    entry_px: float
) -> int:
    """Calculate position size using fixed-fractional method.
    
    Args:
        portfolio_value: Total portfolio value in dollars
        pct_per_trade: Percentage of portfolio to risk per trade (e.g., 0.05 = 5%)
        entry_px: Expected entry price per share
        
    Returns:
        Number of shares to purchase (integer)
        
    Examples:
        >>> shares_fixed_fractional(100000, 0.05, 50.0)
        100  # $100k * 5% / $50 = 100 shares
    """
    # Ensure all inputs are non-negative
    portfolio_value = max(0.0, portfolio_value)
    pct_per_trade = max(0.0, pct_per_trade)
    entry_px = max(1e-9, entry_px)  # Avoid division by zero
    
    # Calculate position value
    position_value = portfolio_value * pct_per_trade
    
    # Calculate number of shares (floor to integer)
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
        
    Examples:
        >>> shares_atr_target(100000, 0.005, 2.0, 3.0)
        83  # $100k * 0.5% / (3.0 * $2.0) = 83 shares
        
    Logic:
        Risk per share = k_atr * atr_points (stop distance)
        Total risk budget = portfolio_value * daily_risk_cap
        Shares = risk_budget / risk_per_share
    """
    # Ensure all inputs are non-negative
    portfolio_value = max(0.0, portfolio_value)
    daily_risk_cap = max(0.0, daily_risk_cap)
    atr_points = max(1e-9, atr_points)  # Avoid division by zero
    k_atr = max(0.0, k_atr)
    
    # Calculate risk budget
    risk_budget = portfolio_value * daily_risk_cap
    
    # Calculate risk per share (stop distance)
    unit_risk = k_atr * atr_points
    
    # Calculate number of shares
    shares = math.floor(risk_budget / unit_risk)
    
    return max(0, shares)
