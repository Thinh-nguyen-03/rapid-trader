"""End-of-Day trading job - generates signals, applies risk controls, creates orders."""

import argparse
import pandas as pd
from datetime import date
from pathlib import Path
from sqlalchemy import text
from ..core.db import get_engine
from ..core.config import settings
from ..core.logging_config import setup_logging, get_logger

logger = get_logger(__name__)
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

    return df.sort_index()


def get_last_session() -> date:
    eng = get_engine()

    with eng.begin() as conn:
        result = conn.execute(text("""
            SELECT MAX(d) FROM bars_daily
        """)).scalar_one()

    return result


def get_portfolio_value() -> float:
    return settings.RT_START_CAPITAL


def get_sector_value(sector: str) -> float:
    eng = get_engine()

    with eng.begin() as conn:
        result = conn.execute(text("""
            SELECT COALESCE(SUM(qty * avg_px), 0)
            FROM positions
            WHERE sector = :sector
        """), {"sector": sector}).scalar_one()

    return float(result or 0.0)


def get_position_quantity(symbol: str) -> int:
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

    setup_logging(
        log_level=settings.RT_LOG_LEVEL,
        json_logs=settings.RT_LOG_JSON,
        log_file=Path(settings.RT_LOG_FILE) if settings.RT_LOG_FILE else None
    )

    try:
        logger.info("job_started", job="eod_trade")

        # Get latest trading session
        trade_date = get_last_session()
        logger.info("processing_signals", trade_date=str(trade_date))
        
        # Update and check kill switch first (includes drawdown check)
        kill_active, kill_reason = update_kill_switch_state(
            trade_date,
            drawdown_threshold=settings.RT_DRAWDOWN_THRESHOLD
        )
        if kill_active:
            logger.warning("kill_switch_active", trade_date=str(trade_date), reason=kill_reason)
            update_filtering_metrics(trade_date, 0, 0)
            return 0

        bear_gate = settings.RT_MARKET_FILTER_ENABLE and not is_bull_market(trade_date)
        if bear_gate:
            from ..core.market_state import get_market_state
            market_info = get_market_state(trade_date)
            spy_close = market_info.get('spy_close', 'N/A')
            spy_sma200 = market_info.get('spy_sma200', 'N/A')
            logger.info("market_filter_active", buys_blocked=True, exits_allowed=True,
                       spy_close=spy_close, spy_sma200=spy_sma200)
        else:
            logger.info("trading_permitted", trade_date=str(trade_date))
        
        # Get active symbols with sector information
        eng = get_engine()
        with eng.begin() as conn:
            symbols_data = conn.execute(text("""
                SELECT symbol, sector FROM symbols 
                WHERE is_active = true 
                ORDER BY symbol
            """)).all()
        
        if not symbols_data:
            logger.warning("no_active_symbols")
            return 0

        logger.info("processing_symbols", count=len(symbols_data))
        
        total_candidates = 0
        filtered_candidates = 0
        signals_generated = 0
        orders_created = 0
        
        portfolio_value = get_portfolio_value()
        logger.info("portfolio_value", value=portfolio_value)

        # Get current positions and their ATR values for risk checks
        current_positions = get_current_positions()
        position_symbols = [p['symbol'] for p in current_positions]
        position_atr_values = get_position_atr_values(position_symbols, settings.RT_ATR_LOOKBACK)

        portfolio_heat_blocked = False
        if settings.RT_PORTFOLIO_HEAT_ENABLE:
            heat_ok, current_heat = portfolio_heat_ok(
                current_positions,
                position_atr_values,
                portfolio_value,
                settings.RT_MAX_PORTFOLIO_HEAT
            )
            if not heat_ok:
                logger.warning("portfolio_heat_exceeded", current=current_heat,
                              limit=settings.RT_MAX_PORTFOLIO_HEAT)
                portfolio_heat_blocked = True
            else:
                logger.info("portfolio_heat_ok", current=current_heat)

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
                    logger.info("vix_scaling_applied", vix=current_vix, multiplier=vix_multiplier)
            else:
                logger.info("vix_data_unavailable")

        for symbol, sector in symbols_data:
            total_candidates += 1
            
            try:
                # Check stop cooldown
                if stop_cooldown_active(symbol, trade_date, settings.RT_COOLDOWN_DAYS_ON_STOP):
                    filtered_candidates += 1
                    continue
                
                df = get_bars(symbol, lookback=250)
                
                if len(df) < 200:
                    filtered_candidates += 1
                    continue
                
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

                        if portfolio_heat_blocked:
                            filtered_candidates += 1
                            record_order(trade_date, symbol, "buy", 0, "portfolio_heat_block")
                            continue

                        # Double-check kill switch for buy orders
                        kill_check, _ = is_kill_switch_active(trade_date)
                        if kill_check:
                            filtered_candidates += 1
                            continue

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
                                record_order(
                                    trade_date,
                                    symbol,
                                    "sell",
                                    0,  # 0 = exit full position
                                    f"mvp-exit-{strategy.lower()}"
                                )
                                orders_created += 1
                
            except Exception as e:
                logger.error("symbol_processing_error", symbol=symbol, error=str(e))
                filtered_candidates += 1
                continue
        
        # Update filtering metrics
        update_filtering_metrics(trade_date, total_candidates, filtered_candidates)

        # Log summary
        pct_filtered = 100.0 * filtered_candidates / total_candidates if total_candidates > 0 else 0.0
        logger.info("job_summary",
                   trade_date=str(trade_date),
                   total_candidates=total_candidates,
                   filtered_candidates=filtered_candidates,
                   pct_filtered=pct_filtered,
                   signals_generated=signals_generated,
                   orders_created=orders_created)

        logger.info("job_completed", job="eod_trade")
        return 0

    except Exception as e:
        logger.exception("job_failed", job="eod_trade", error=str(e))
        return 1


if __name__ == "__main__":
    exit(main())
