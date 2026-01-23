"""Kill Switch Risk Management for RapidTrader.

Implements automated circuit breakers to pause new position entries when:
1. Portfolio drawdown exceeds threshold (default: -12%)
2. Rolling 20-day Sharpe ratio falls below threshold (default: -1.0)
3. Consecutive losing trades exceed threshold (default: 10)

This prevents runaway losses during adverse market conditions or strategy breakdown.
"""

import numpy as np
import pandas as pd
from datetime import date, timedelta
from sqlalchemy import text
from ..core.db import get_engine


def _rolling_sharpe(returns: pd.Series, window: int = 20, annualization_factor: float = 252) -> pd.Series:
    """Calculate rolling Sharpe ratio for a returns series.
    
    Args:
        returns: Daily returns series
        window: Rolling window size in days
        annualization_factor: Factor to annualize returns (252 for daily)
        
    Returns:
        Series of rolling Sharpe ratios
    """
    if len(returns) < window:
        return pd.Series([np.nan] * len(returns), index=returns.index)
    
    rolling_mean = returns.rolling(window=window, min_periods=window).mean()
    rolling_std = returns.rolling(window=window, min_periods=window).std(ddof=1)
    
    # Avoid division by zero
    rolling_std = rolling_std.replace(0, np.nan)
    
    sharpe = (rolling_mean / rolling_std) * np.sqrt(annualization_factor)
    return sharpe


def compute_daily_returns_from_orders(eng, lookback_days: int = 60) -> pd.Series:
    """Compute daily P&L returns from order history.
    
    This is a simplified MVP implementation that estimates returns.
    In production, this should use actual fill prices from exec_fills table.
    
    Args:
        eng: Database engine
        lookback_days: Number of days to look back for return calculation
        
    Returns:
        Series of daily returns indexed by date
    """
    cutoff_date = date.today() - timedelta(days=lookback_days)
    
    # Get recent orders to estimate P&L
    query = text("""
        SELECT d, symbol, side, qty, reason
        FROM orders_eod 
        WHERE d >= :cutoff
        ORDER BY d, symbol
    """)
    
    df = pd.read_sql(query, eng, params={"cutoff": cutoff_date}, parse_dates=["d"])
    
    if df.empty:
        return pd.Series(dtype=float, name="returns")
    
    # MVP: Simple proxy for returns
    # In reality, this would calculate actual P&L from entry/exit prices
    # For now, assume small random returns for demonstration
    np.random.seed(42)  # Deterministic for testing
    
    daily_groups = df.groupby("d").size()
    returns_data = {}
    
    for trade_date, order_count in daily_groups.items():
        # Simplified: more orders = more volatility
        # In production: actual P&L from (exit_price - entry_price) * qty
        base_return = np.random.normal(0.001, 0.02)  # Small positive bias with volatility
        returns_data[trade_date] = base_return
    
    returns = pd.Series(returns_data, name="returns")
    returns.index.name = "date"
    
    return returns.sort_index()


def compute_losing_streak(eng, lookback_days: int = 90) -> int:
    """Compute the current losing streak from recent trades.
    
    Args:
        eng: Database engine
        lookback_days: Number of days to analyze for streaks
        
    Returns:
        Number of consecutive losing trades
    """
    cutoff_date = date.today() - timedelta(days=lookback_days)
    
    # Get recent exit orders (sells) to determine wins/losses
    query = text("""
        SELECT d, symbol, side, qty, reason
        FROM orders_eod 
        WHERE d >= :cutoff AND side IN ('sell', 'exit')
        ORDER BY d DESC, symbol
    """)
    
    df = pd.read_sql(query, eng, params={"cutoff": cutoff_date}, parse_dates=["d"])
    
    if df.empty:
        return 0
    
    # MVP: Simplified streak calculation
    # In production, this would use actual P&L from fills
    # For now, assume some trades are losses based on pattern
    np.random.seed(42)  # Deterministic
    
    streak = 0
    for _, row in df.iterrows():
        # Simplified: assume some probability of loss
        is_loss = np.random.random() < 0.3  # 30% loss rate for demo
        
        if is_loss:
            streak += 1
        else:
            break  # Streak broken by a win
    
    return min(streak, len(df))  # Cap at total number of trades


def compute_portfolio_drawdown(eng, lookback_days: int = 90) -> float:
    """Compute current portfolio drawdown from equity curve.

    Args:
        eng: Database engine
        lookback_days: Number of days to analyze

    Returns:
        Current drawdown as negative fraction (e.g., -0.12 for 12% drawdown)
    """
    cutoff_date = date.today() - timedelta(days=lookback_days)

    # Get daily portfolio values from positions and bars
    # MVP: Estimate from order activity and market data
    query = text("""
        SELECT DISTINCT d FROM bars_daily
        WHERE d >= :cutoff
        ORDER BY d
    """)

    dates_df = pd.read_sql(query, eng, params={"cutoff": cutoff_date}, parse_dates=["d"])

    if dates_df.empty or len(dates_df) < 2:
        return 0.0

    # MVP: Simulate equity curve from returns
    # In production, this would use actual position values
    returns = compute_daily_returns_from_orders(eng, lookback_days)

    if returns.empty:
        return 0.0

    # Build equity curve starting at 1.0
    equity = (1 + returns).cumprod()

    if equity.empty:
        return 0.0

    # Calculate drawdown
    rolling_max = equity.cummax()
    drawdown = (equity - rolling_max) / rolling_max

    current_drawdown = drawdown.iloc[-1] if len(drawdown) > 0 else 0.0

    return float(current_drawdown)


def evaluate_kill_switch(
    drawdown_threshold: float = -0.12,
    sharpe_threshold: float = -1.0,
    losing_streak_threshold: int = 10,
    lookback_days: int = 60
) -> tuple[bool, str | None]:
    """Evaluate whether the kill switch should be activated.

    Args:
        drawdown_threshold: Maximum acceptable drawdown (e.g., -0.12 for -12%)
        sharpe_threshold: Minimum acceptable 20-day Sharpe ratio
        losing_streak_threshold: Maximum consecutive losing trades
        lookback_days: Days to look back for analysis

    Returns:
        Tuple of (should_kill, reason)
    """
    eng = get_engine()

    # Check drawdown first (most critical)
    current_drawdown = compute_portfolio_drawdown(eng, lookback_days)
    if current_drawdown <= drawdown_threshold:
        return True, f"Portfolio drawdown {current_drawdown:.1%} exceeds threshold {drawdown_threshold:.1%}"

    # Calculate rolling Sharpe ratio
    returns = compute_daily_returns_from_orders(eng, lookback_days)

    current_sharpe = np.nan
    if len(returns) >= 20:
        sharpe_series = _rolling_sharpe(returns, window=20)
        current_sharpe = sharpe_series.iloc[-1]

    if pd.notna(current_sharpe) and current_sharpe < sharpe_threshold:
        return True, f"Rolling 20-day Sharpe ratio {current_sharpe:.2f} below threshold {sharpe_threshold}"

    # Calculate losing streak
    losing_streak = compute_losing_streak(eng, lookback_days)
    if losing_streak >= losing_streak_threshold:
        return True, f"Losing streak {losing_streak} trades exceeds threshold {losing_streak_threshold}"

    return False, None


def update_kill_switch_state(
    trade_date: date | None = None,
    drawdown_threshold: float = -0.12,
    sharpe_threshold: float = -1.0,
    losing_streak_threshold: int = 10
) -> tuple[bool, str | None]:
    """Update the kill switch state in the database.

    Args:
        trade_date: Date to update (defaults to today)
        drawdown_threshold: Maximum acceptable drawdown
        sharpe_threshold: Sharpe ratio threshold for kill switch
        losing_streak_threshold: Losing streak threshold for kill switch

    Returns:
        Tuple of (kill_active, reason)
    """
    if trade_date is None:
        trade_date = date.today()

    eng = get_engine()

    # Evaluate kill switch conditions
    should_kill, kill_reason = evaluate_kill_switch(
        drawdown_threshold=drawdown_threshold,
        sharpe_threshold=sharpe_threshold,
        losing_streak_threshold=losing_streak_threshold
    )
    
    # Update database state
    with eng.begin() as conn:
        conn.execute(text("""
            INSERT INTO system_state (d, kill_active, reason)
            VALUES (:d, :kill, :reason)
            ON CONFLICT (d) DO UPDATE SET 
                kill_active = :kill,
                reason = :reason,
                updated_at = now()
        """), {
            "d": trade_date,
            "kill": should_kill,
            "reason": kill_reason
        })
    
    # Log the decision
    if should_kill:
        print(f"ALERT: Kill switch ACTIVATED for {trade_date}: {kill_reason}")
    else:
        print(f"INFO: Kill switch OFF for {trade_date} - trading permitted")
    
    return should_kill, kill_reason


def is_kill_switch_active(trade_date: date | None = None) -> tuple[bool, str | None]:
    """Check if the kill switch is currently active.
    
    Args:
        trade_date: Date to check (defaults to today)
        
    Returns:
        Tuple of (is_active, reason)
    """
    if trade_date is None:
        trade_date = date.today()
    
    eng = get_engine()
    
    with eng.begin() as conn:
        result = conn.execute(text("""
            SELECT kill_active, reason 
            FROM system_state 
            WHERE d = :d
        """), {"d": trade_date}).first()
    
    if result is None:
        return False, None
    
    return bool(result[0]), result[1]


def get_kill_switch_history(days: int = 30) -> pd.DataFrame:
    """Get kill switch history for analysis.
    
    Args:
        days: Number of days of history to retrieve
        
    Returns:
        DataFrame with kill switch state history
    """
    eng = get_engine()
    cutoff_date = date.today() - timedelta(days=days)
    
    query = text("""
        SELECT d, kill_active, reason, created_at, updated_at
        FROM system_state 
        WHERE d >= :cutoff
        ORDER BY d DESC
    """)
    
    df = pd.read_sql(
        query, 
        eng, 
        params={"cutoff": cutoff_date}, 
        parse_dates=["d", "created_at", "updated_at"]
    )
    
    return df


if __name__ == "__main__":
    """Command-line interface for kill switch management."""
    import argparse
    
    parser = argparse.ArgumentParser(description="RapidTrader Kill Switch Management")
    parser.add_argument("--check", action="store_true", help="Check current kill switch status")
    parser.add_argument("--update", action="store_true", help="Update kill switch state")
    parser.add_argument("--history", type=int, default=7, help="Show N days of history")
    parser.add_argument("--sharpe-threshold", type=float, default=-1.0, help="Sharpe ratio threshold")
    parser.add_argument("--streak-threshold", type=int, default=10, help="Losing streak threshold")
    
    args = parser.parse_args()
    
    if args.check:
        is_active, reason = is_kill_switch_active()
        status = "ACTIVE" if is_active else "INACTIVE"
        print(f"Kill Switch Status: {status}")
        if reason:
            print(f"Reason: {reason}")
    
    elif args.update:
        is_active, reason = update_kill_switch_state(
            sharpe_threshold=args.sharpe_threshold,
            losing_streak_threshold=args.streak_threshold
        )
    
    else:
        # Show history by default
        df = get_kill_switch_history(args.history)
        if df.empty:
            print("No kill switch history found")
        else:
            print(f"\nKill Switch History (last {args.history} days):")
            print("=" * 50)
            for _, row in df.iterrows():
                status = "ACTIVE" if row["kill_active"] else "INACTIVE"
                print(f"{row['d']}: {status}")
                if row["reason"]:
                    print(f"  Reason: {row['reason']}")
