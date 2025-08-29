"""End-of-Day Trading Job for RapidTrader.

Generates trading signals using RSI mean-reversion and SMA crossover strategies,
applies risk management controls, and creates dry-run orders.
"""

import argparse
import pandas as pd
from datetime import date
from sqlalchemy import text
from ..core.db import get_engine
from ..core.config import settings
from ..indicators.core import atr
from ..strategies.rsi_mr import rsi_mean_reversion
from ..strategies.sma_cross import sma_crossover
from ..risk.sizing import shares_fixed_fractional, shares_atr_target
from ..risk.controls import sector_exposure_ok
from ..risk.stop_cooldown import stop_cooldown_active
from ..core.market_state import is_bull_market


def get_bars(symbol: str, lookback: int = 250) -> pd.DataFrame:
    """Get historical OHLCV bars for a symbol.
    
    Args:
        symbol: Stock symbol
        lookback: Number of days to retrieve (default 250)
        
    Returns:
        DataFrame with OHLCV data indexed by date
    """
    eng = get_engine()
    
    query = text("""
        SELECT d, open, high, low, close, volume 
        FROM bars_daily 
        WHERE symbol = :symbol 
        ORDER BY d DESC
        LIMIT :lookback
    """)
    
    df = pd.read_sql(
        query, 
        eng, 
        params={"symbol": symbol, "lookback": lookback}, 
        parse_dates=["d"]
    ).set_index("d")
    
    # Sort by date (oldest first) for calculations
    return df.sort_index()


def get_last_session() -> date:
    """Get the most recent trading session date.
    
    Returns:
        Date of the most recent data in bars_daily table
    """
    eng = get_engine()
    
    with eng.begin() as conn:
        result = conn.execute(text("""
            SELECT MAX(d) FROM bars_daily
        """)).scalar_one()
    
    return result


def get_portfolio_value() -> float:
    """Get current portfolio value for position sizing.
    
    Returns:
        Portfolio value in dollars (uses RT_START_CAPITAL for MVP)
    """
    # For MVP, use static starting capital
    # In production, this would calculate actual portfolio value
    return settings.RT_START_CAPITAL


def get_sector_value(sector: str) -> float:
    """Get current dollar value invested in a sector.
    
    Args:
        sector: Sector name
        
    Returns:
        Current sector exposure in dollars
    """
    eng = get_engine()
    
    with eng.begin() as conn:
        result = conn.execute(text("""
            SELECT COALESCE(SUM(qty * avg_px), 0) 
            FROM positions 
            WHERE sector = :sector
        """), {"sector": sector}).scalar_one()
    
    return float(result or 0.0)


def record_signal(trade_date: date, symbol: str, strategy: str, direction: str, strength: float = 1.0):
    """Record a trading signal in the database.
    
    Args:
        trade_date: Trading date
        symbol: Stock symbol  
        strategy: Strategy name (e.g., 'RSI_MR', 'SMA_X')
        direction: Signal direction ('buy', 'sell', 'hold')
        strength: Signal strength (0.0 to 1.0)
    """
    eng = get_engine()
    
    with eng.begin() as conn:
        conn.execute(text("""
            INSERT INTO signals_daily (d, symbol, strategy, direction, strength)
            VALUES (:d, :symbol, :strategy, :direction, :strength)
            ON CONFLICT (d, symbol, strategy) DO UPDATE SET 
                direction = :direction, strength = :strength
        """), {
            "d": trade_date,
            "symbol": symbol,
            "strategy": strategy,
            "direction": direction,
            "strength": strength
        })


def record_order(trade_date: date, symbol: str, side: str, quantity: int, reason: str):
    """Record a trading order in the database.
    
    Args:
        trade_date: Trading date
        symbol: Stock symbol
        side: Order side ('buy', 'sell', 'exit')
        quantity: Number of shares
        reason: Order reason/description
    """
    eng = get_engine()
    
    with eng.begin() as conn:
        conn.execute(text("""
            INSERT INTO orders_eod (d, symbol, side, qty, type, reason)
            VALUES (:d, :symbol, :side, :qty, 'market', :reason)
        """), {
            "d": trade_date,
            "symbol": symbol,
            "side": side,
            "qty": quantity,
            "reason": reason
        })


def update_filtering_metrics(trade_date: date, total_candidates: int, filtered_candidates: int):
    """Update market state with filtering statistics.
    
    Args:
        trade_date: Trading date
        total_candidates: Total symbols processed
        filtered_candidates: Number of symbols filtered out
    """
    eng = get_engine()
    
    pct_filtered = 0.0 if total_candidates == 0 else 100.0 * filtered_candidates / total_candidates
    
    with eng.begin() as conn:
        conn.execute(text("""
            UPDATE market_state 
            SET total_candidates = :total,
                filtered_candidates = :filtered,
                pct_entries_filtered = :pct
            WHERE d = :d
        """), {
            "d": trade_date,
            "total": total_candidates,
            "filtered": filtered_candidates,
            "pct": pct_filtered
        })


def main():
    """Main EOD trading job entry point."""
    parser = argparse.ArgumentParser(
        description="RapidTrader End-of-Day Trading Job"
    )
    parser.add_argument(
        "--mode", 
        choices=["dry_run"], 
        default="dry_run",
        help="Trading mode (currently only dry_run supported)"
    )
    parser.add_argument(
        "--signals-only",
        action="store_true",
        help="Generate signals only, don't create orders"
    )
    
    args = parser.parse_args()
    
    try:
        print("Starting EOD trading job...")
        
        # Get latest trading session
        trade_date = get_last_session()
        print(f"Processing signals for {trade_date}")
        
        # Check market filter
        if settings.RT_MARKET_FILTER_ENABLE and not is_bull_market(trade_date):
            print(f"{trade_date}: Market filter OFF — no new entries allowed")
            update_filtering_metrics(trade_date, 0, 0)
            return 0
        
        # Get active symbols with sector information
        eng = get_engine()
        with eng.begin() as conn:
            symbols_data = conn.execute(text("""
                SELECT symbol, sector FROM symbols 
                WHERE is_active = true 
                ORDER BY symbol
            """)).all()
        
        if not symbols_data:
            print("No active symbols found")
            return 0
        
        print(f"Processing {len(symbols_data)} symbols...")
        
        # Initialize counters
        total_candidates = 0
        filtered_candidates = 0
        signals_generated = 0
        orders_created = 0
        
        portfolio_value = get_portfolio_value()
        print(f"Portfolio value: ${portfolio_value:,.2f}")
        
        # Process each symbol
        for symbol, sector in symbols_data:
            total_candidates += 1
            
            try:
                # Check stop cooldown
                if stop_cooldown_active(symbol, trade_date, settings.RT_COOLDOWN_DAYS_ON_STOP):
                    filtered_candidates += 1
                    continue
                
                # Get historical data
                df = get_bars(symbol, lookback=250)
                
                if len(df) < 200:  # Need sufficient data for calculations
                    filtered_candidates += 1
                    continue
                
                # Generate strategy signals
                rsi_result = rsi_mean_reversion(
                    df, 
                    window=settings.RT_CONFIRM_WINDOW,
                    min_count=settings.RT_CONFIRM_MIN_COUNT
                )
                rsi_signal = rsi_result.iloc[-1]["signal"]
                
                sma_result = sma_crossover(df)
                sma_signal = sma_result.iloc[-1]["signal"]
                
                # Determine final signal (priority: sell > buy > hold)
                final_signal = "hold"
                strategy = None
                
                if rsi_signal == "sell" or sma_signal == "sell":
                    final_signal = "sell"
                    strategy = "RSI_MR" if rsi_signal == "sell" else "SMA_X"
                elif rsi_signal == "buy" or sma_signal == "buy":
                    final_signal = "buy"
                    strategy = "RSI_MR" if rsi_signal == "buy" else "SMA_X"
                
                # Record signals for both strategies
                record_signal(trade_date, symbol, "RSI_MR", rsi_signal)
                record_signal(trade_date, symbol, "SMA_X", sma_signal)
                
                if final_signal != "hold":
                    signals_generated += 1
                    
                    # Skip order creation if signals-only mode
                    if args.signals_only:
                        continue
                    
                    # Get current price and calculate position size
                    current_price = float(df["close"].iloc[-1])
                    
                    if final_signal == "buy":
                        # Calculate position size using both methods
                        atr_14 = float(atr(df["high"], df["low"], df["close"], settings.RT_ATR_LOOKBACK).iloc[-1])
                        
                        qty_ff = shares_fixed_fractional(
                            portfolio_value, 
                            settings.RT_PCT_PER_TRADE, 
                            current_price
                        )
                        
                        qty_atr = shares_atr_target(
                            portfolio_value,
                            settings.RT_DAILY_RISK_CAP,
                            atr_14,
                            settings.RT_ATR_STOP_K
                        )
                        
                        # Use smaller of the two sizes
                        quantity = min(qty_ff, qty_atr)
                        
                        if quantity > 0:
                            # Check sector exposure limits
                            current_sector_value = get_sector_value(sector or "")
                            candidate_value = quantity * current_price
                            
                            if sector_exposure_ok(
                                current_sector_value,
                                portfolio_value,
                                candidate_value,
                                settings.RT_MAX_EXPOSURE_PER_SECTOR
                            ):
                                # Create buy order
                                record_order(
                                    trade_date, 
                                    symbol, 
                                    "buy", 
                                    quantity, 
                                    f"mvp-entry-{strategy.lower()}"
                                )
                                orders_created += 1
                            else:
                                filtered_candidates += 1
                        
                    elif final_signal == "sell":
                        # Create exit order (quantity 0 indicates full position exit)
                        record_order(
                            trade_date,
                            symbol,
                            "sell",
                            0,  # 0 = exit full position
                            f"mvp-exit-{strategy.lower()}"
                        )
                        orders_created += 1
                
            except Exception as e:
                print(f"Error processing {symbol}: {e}")
                filtered_candidates += 1
                continue
        
        # Update filtering metrics
        update_filtering_metrics(trade_date, total_candidates, filtered_candidates)
        
        # Print summary
        pct_filtered = 100.0 * filtered_candidates / total_candidates if total_candidates > 0 else 0.0
        print(f"\nEOD Trading Job Summary for {trade_date}:")
        print(f"  Total candidates: {total_candidates}")
        print(f"  Filtered out: {filtered_candidates} ({pct_filtered:.1f}%)")
        print(f"  Signals generated: {signals_generated}")
        print(f"  Orders created: {orders_created}")
        
        print("EOD trading job completed successfully")
        return 0
        
    except Exception as e:
        print(f"EOD trading job failed: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
