"""Summary and reporting utilities for daily jobs.

This module provides functions for generating daily summaries
and printing trading activity reports.
"""

from datetime import date
from sqlalchemy import text
from rapidtrader.core.db import get_engine


def print_daily_summary(trade_date: date):
    """Print an enhanced summary of the day's trading activity.
    
    Args:
        trade_date: The trading date to summarize
    """
    eng = get_engine()
    
    with eng.begin() as conn:
        # Get signal counts
        signal_stats = conn.execute(text("""
            SELECT direction, COUNT(*) as count
            FROM signals_daily 
            WHERE d = :d
            GROUP BY direction
            ORDER BY direction
        """), {"d": trade_date}).all()
        
        # Get order counts with breakdown by reason
        order_stats = conn.execute(text("""
            SELECT side, COUNT(*) as count, SUM(qty) as total_qty
            FROM orders_eod 
            WHERE d = :d
            GROUP BY side
            ORDER BY side
        """), {"d": trade_date}).all()
        
        # Get blocked buy count
        blocked_buys = conn.execute(text("""
            SELECT COUNT(*) 
            FROM orders_eod 
            WHERE d = :d AND side = 'buy' AND qty = 0 AND reason = 'market_gate_block'
        """), {"d": trade_date}).scalar() or 0
        
        # Get actual position exits
        position_exits = conn.execute(text("""
            SELECT COUNT(*) 
            FROM orders_eod o
            JOIN positions p USING(symbol)
            WHERE o.d = :d AND o.side = 'sell' AND p.qty > 0
        """), {"d": trade_date}).scalar() or 0
        
        # Get enhanced market state with SPY data
        market_info = conn.execute(text("""
            SELECT bull_gate, pct_entries_filtered, total_candidates, filtered_candidates,
                   spy_close, spy_sma200
            FROM market_state 
            WHERE d = :d
        """), {"d": trade_date}).first()
        
        print(f"\n=== Daily Summary for {trade_date} ===")
        
        if market_info:
            bull_gate, pct_filtered, total, filtered, spy_close, spy_sma200 = market_info
            
            # Enhanced market state display
            market_regime = 'BULL' if bull_gate else 'BEAR'
            print(f"Market Filter: {market_regime} (SPY >= 200-SMA: {bull_gate})")
            
            if spy_close and spy_sma200:
                spy_vs_sma = "above" if spy_close >= spy_sma200 else "below"
                print(f"SPY: ${spy_close:.2f} ({spy_vs_sma} 200-SMA: ${spy_sma200:.2f})")
            elif spy_close:
                print(f"SPY Close: ${spy_close:.2f}")
            
            print(f"Filtering: {filtered or 0}/{total or 0} candidates filtered ({pct_filtered or 0:.1f}%)")
            
            if blocked_buys > 0:
                print(f"Market Gate: {blocked_buys} buy orders blocked")
        
        print("\nSignals Generated:")
        for direction, count in signal_stats:
            print(f"  {direction.upper()}: {count}")
        
        print("\nOrders Created:")
        for side, count, total_qty in order_stats:
            print(f"  {side.upper()}: {count} orders, {total_qty or 0} total shares")
        
        if position_exits > 0:
            print(f"  Actual position exits: {position_exits}")
        
        print("=" * 40)
