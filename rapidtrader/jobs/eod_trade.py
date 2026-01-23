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
from ..risk.sizing import shares_fixed_fractional, shares_atr_target, compute_position_size
from ..risk.controls import (
    sector_exposure_ok,
    portfolio_heat_ok,
    get_current_positions,
    get_position_atr_values,
    vix_scale_factor,
    get_current_vix,
    correlation_ok
)
from ..risk.stop_cooldown import stop_cooldown_active
from ..core.market_state import is_bull_market
from ..risk.kill_switch import is_kill_switch_active, update_kill_switch_state


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


def get_position_quantity(symbol: str) -> int:
    """Get current position quantity for a symbol.
    
    Args:
        symbol: Stock symbol
        
    Returns:
        Current position quantity (0 if no position)
    """
    eng = get_engine()
    
    try:
        with eng.begin() as conn:
            result = conn.execute(text("""
                SELECT COALESCE(qty, 0) 
                FROM positions 
                WHERE symbol = :symbol
            """), {"symbol": symbol}).scalar()
            
            return int(result or 0)
            
    except Exception:
        return 0


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
        
        # Update and check kill switch first (includes drawdown check)
        kill_active, kill_reason = update_kill_switch_state(
            trade_date,
            drawdown_threshold=settings.RT_DRAWDOWN_THRESHOLD
        )
        if kill_active:
            print(f"ALERT: Kill switch ACTIVE for {trade_date}: {kill_reason}")
            print("WARNING: No new entries allowed - system in protective mode")
            update_filtering_metrics(trade_date, 0, 0)
            return 0
        
        # Check market filter but don't return early
        bear_gate = settings.RT_MARKET_FILTER_ENABLE and not is_bull_market(trade_date)
        if bear_gate:
            # Get market state info for enhanced logging
            from ..core.market_state import get_market_state
            market_info = get_market_state(trade_date)
            spy_close = market_info.get('spy_close', 'N/A')
            spy_sma200 = market_info.get('spy_sma200', 'N/A')
            print(f"{trade_date}: Market filter OFF — buys blocked, exits allowed.")
            print(f"INFO: SPY close: {spy_close}, SMA200: {spy_sma200}")
        else:
            print(f"INFO: Kill switch OFF for {trade_date} - trading permitted")
        
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

        # Get current positions and their ATR values for risk checks
        current_positions = get_current_positions()
        position_symbols = [p['symbol'] for p in current_positions]
        position_atr_values = get_position_atr_values(position_symbols, settings.RT_ATR_LOOKBACK)

        # Check portfolio heat limit
        portfolio_heat_blocked = False
        if settings.RT_PORTFOLIO_HEAT_ENABLE:
            heat_ok, current_heat = portfolio_heat_ok(
                current_positions,
                position_atr_values,
                portfolio_value,
                settings.RT_MAX_PORTFOLIO_HEAT
            )
            if not heat_ok:
                print(f"WARNING: Portfolio heat {current_heat:.1%} exceeds limit {settings.RT_MAX_PORTFOLIO_HEAT:.1%}")
                print("INFO: New entries blocked until heat reduces")
                portfolio_heat_blocked = True
            else:
                print(f"INFO: Portfolio heat {current_heat:.1%} within limit")

        # Get VIX for position scaling
        vix_multiplier = 1.0
        if settings.RT_VIX_SCALING_ENABLE:
            current_vix = get_current_vix()
            if current_vix is not None:
                vix_multiplier = vix_scale_factor(
                    current_vix,
                    settings.RT_VIX_THRESHOLD_ELEVATED,
                    settings.RT_VIX_THRESHOLD_HIGH,
                    settings.RT_VIX_SCALE_ELEVATED,
                    settings.RT_VIX_SCALE_HIGH
                )
                if vix_multiplier < 1.0:
                    print(f"INFO: VIX at {current_vix:.1f}, position size scaled to {vix_multiplier:.0%}")
            else:
                print("INFO: VIX data not available, using full position size")

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
                
                # Always record signals for analytics (regardless of market gate)
                record_signal(trade_date, symbol, "RSI_MR", rsi_signal)
                record_signal(trade_date, symbol, "SMA_X", sma_signal)
                
                if final_signal != "hold":
                    signals_generated += 1
                    
                    # Skip order creation if signals-only mode
                    if args.signals_only:
                        continue
                    
                    # Get current price for order processing
                    current_price = float(df["close"].iloc[-1])
                    
                    if final_signal == "buy":
                        # Gate buy orders when bear_gate is active
                        if bear_gate:
                            filtered_candidates += 1
                            record_order(trade_date, symbol, "buy", 0, "market_gate_block")
                            continue

                        # Block if portfolio heat exceeded
                        if portfolio_heat_blocked:
                            filtered_candidates += 1
                            record_order(trade_date, symbol, "buy", 0, "portfolio_heat_block")
                            continue

                        # Double-check kill switch for buy orders
                        kill_check, _ = is_kill_switch_active(trade_date)
                        if kill_check:
                            filtered_candidates += 1
                            continue

                        # Check correlation with existing positions
                        if settings.RT_CORRELATION_CHECK_ENABLE and current_positions:
                            corr_ok, correlated_with = correlation_ok(
                                symbol,
                                current_positions,
                                settings.RT_CORRELATION_THRESHOLD,
                                settings.RT_CORRELATION_LOOKBACK,
                                settings.RT_CORRELATION_TOP_N
                            )
                            if not corr_ok:
                                filtered_candidates += 1
                                record_order(trade_date, symbol, "buy", 0, f"correlation_block:{correlated_with}")
                                continue

                        # Calculate position size with VIX scaling
                        atr_14 = float(atr(df["high"], df["low"], df["close"], settings.RT_ATR_LOOKBACK).iloc[-1])

                        quantity = compute_position_size(
                            portfolio_value=portfolio_value,
                            entry_px=current_price,
                            atr_points=atr_14,
                            pct_per_trade=settings.RT_PCT_PER_TRADE,
                            daily_risk_cap=settings.RT_DAILY_RISK_CAP,
                            k_atr=settings.RT_ATR_STOP_K,
                            vix_multiplier=vix_multiplier
                        )

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
                                record_order(trade_date, symbol, "buy", 0, "sector_exposure_block")
                        
                    elif final_signal == "sell":
                        # Allow sell/exit orders regardless of bear_gate (if config permits)
                        if not bear_gate or settings.RT_ALLOW_EXITS_IN_BEAR:
                            # Check if we should filter sells to held positions only
                            should_create_sell = True
                            if settings.RT_SELLS_HELD_POSITIONS_ONLY:
                                position_qty = get_position_quantity(symbol)
                                should_create_sell = position_qty > 0
                            
                            if should_create_sell:
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
