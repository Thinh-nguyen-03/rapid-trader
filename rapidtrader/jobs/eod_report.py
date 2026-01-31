"""End-of-Day Reporting Job for RapidTrader.

Generates daily summary reports showing trading activity, filtering metrics,
and system performance statistics."""

import argparse
from datetime import date
from sqlalchemy import text
from ..core.db import get_engine


def get_latest_trading_date() -> date:
    """Get the most recent trading date with data."""
    eng = get_engine()
    
    with eng.begin() as conn:
        result = conn.execute(text("""
            SELECT MAX(d) FROM market_state WHERE d IS NOT NULL
        """)).scalar()
    
    return result if result else date.today()

def get_market_summary(trade_date: date) -> dict:
    """Get market state summary for a trading date."""
    eng = get_engine()
    
    with eng.begin() as conn:
        result = conn.execute(text("""
            SELECT 
                spy_close,
                spy_sma200,
                bull_gate,
                total_candidates,
                filtered_candidates,
                pct_entries_filtered
            FROM market_state 
            WHERE d = :date
        """), {"date": trade_date}).first()
    
    if result:
        return {
            "spy_close": result[0],
            "spy_sma200": result[1], 
            "bull_gate": result[2],
            "total_candidates": result[3] or 0,
            "filtered_candidates": result[4] or 0,
            "pct_entries_filtered": result[5] or 0.0
        }
    else:
        return {
            "spy_close": None,
            "spy_sma200": None,
            "bull_gate": False,
            "total_candidates": 0,
            "filtered_candidates": 0,
            "pct_entries_filtered": 0.0
        }

def get_signal_summary(trade_date: date) -> dict:
    """Get trading signal summary for a date."""
    eng = get_engine()
    
    with eng.begin() as conn:
        signal_results = conn.execute(text("""
            SELECT strategy, direction, COUNT(*) as count
            FROM signals_daily 
            WHERE d = :date
            GROUP BY strategy, direction
            ORDER BY strategy, direction
        """), {"date": trade_date}).all()
        
        total_signals = conn.execute(text("""
            SELECT COUNT(DISTINCT symbol) as count
            FROM signals_daily 
            WHERE d = :date AND direction != 'hold'
        """), {"date": trade_date}).scalar() or 0
    
    signals_by_strategy = {}
    for strategy, direction, count in signal_results:
        if strategy not in signals_by_strategy:
            signals_by_strategy[strategy] = {}
        signals_by_strategy[strategy][direction] = count
    
    return {
        "total_signals": total_signals,
        "by_strategy": signals_by_strategy
    }

def get_order_summary(trade_date: date) -> dict:
    """Get order summary for a trading date."""
    eng = get_engine()
    
    with eng.begin() as conn:
        order_counts = conn.execute(text("""
            SELECT side, COUNT(*) as count
            FROM orders_eod 
            WHERE d = :date
            GROUP BY side
        """), {"date": trade_date}).all()
        
        order_details = conn.execute(text("""
            SELECT symbol, side, qty, reason
            FROM orders_eod 
            WHERE d = :date
            ORDER BY side, symbol
        """), {"date": trade_date}).all()
    
    counts = {"buy": 0, "sell": 0, "exit": 0}
    for side, count in order_counts:
        counts[side] = count
    
    return {
        "counts": counts,
        "total_orders": sum(counts.values()),
        "details": order_details
    }

def print_market_report(trade_date: date, market_data: dict):
    """Print market state section of the report."""
    print("=" * 60)
    print(f"RAPIDTRADER EOD REPORT - {trade_date}")
    print("=" * 60)
    print()
    
    print("MARKET STATE:")
    print(f"  SPY Close: ${market_data['spy_close']:.2f}" if market_data['spy_close'] else "  SPY Close: N/A")
    print(f"  SPY SMA200: ${market_data['spy_sma200']:.2f}" if market_data['spy_sma200'] else "  SPY SMA200: N/A")
    print(f"  Market Gate: {'BULL' if market_data['bull_gate'] else 'BEAR'} (new entries {'allowed' if market_data['bull_gate'] else 'blocked'})")
    print()

def print_filtering_report(market_data: dict):
    """Print filtering metrics section of the report."""
    print("FILTERING METRICS:")
    print(f"  Total Candidates: {market_data['total_candidates']}")
    print(f"  Filtered Out: {market_data['filtered_candidates']}")
    print(f"  Filter Rate: {market_data['pct_entries_filtered']:.1f}%")
    print()

def print_signal_report(signal_data: dict):
    """Print signal generation section of the report."""
    print("SIGNAL GENERATION:")
    print(f"  Symbols with Signals: {signal_data['total_signals']}")
    
    if signal_data['by_strategy']:
        for strategy, directions in signal_data['by_strategy'].items():
            print(f"  {strategy}:")
            for direction, count in directions.items():
                print(f"    {direction}: {count}")
    else:
        print("  No signals generated")
    print()

def print_order_report(order_data: dict):
    """Print order creation section of the report."""
    print("ORDER CREATION:")
    print(f"  Total Orders: {order_data['total_orders']}")
    print(f"  Buy Orders: {order_data['counts']['buy']}")
    print(f"  Sell Orders: {order_data['counts']['sell']}")
    print(f"  Exit Orders: {order_data['counts']['exit']}")
    print()
    
    if order_data['details']:
        print("ORDER DETAILS:")
        for symbol, side, qty, reason in order_data['details']:
            if side == "buy":
                print(f"  {symbol}: BUY {qty} shares ({reason})")
            else:
                print(f"  {symbol}: {side.upper()} ({reason})")
    else:
        print("  No orders created")
    print()

def main():
    """Main EOD reporting job entry point."""
    parser = argparse.ArgumentParser(
        description="RapidTrader End-of-Day Reporting Job"
    )
    parser.add_argument(
        "--date",
        type=str,
        help="Specific date to report on (YYYY-MM-DD format, defaults to latest)"
    )
    parser.add_argument(
        "--summary-only",
        action="store_true",
        help="Show summary metrics only, skip order details"
    )
    
    args = parser.parse_args()
    
    try:
        # Determine reporting date
        if args.date:
            from datetime import datetime
            trade_date = datetime.strptime(args.date, "%Y-%m-%d").date()
        else:
            trade_date = get_latest_trading_date()
        
        # Gather report data
        market_data = get_market_summary(trade_date)
        signal_data = get_signal_summary(trade_date)
        order_data = get_order_summary(trade_date)
        
        # Print report sections
        print_market_report(trade_date, market_data)
        print_filtering_report(market_data)
        print_signal_report(signal_data)
        
        if args.summary_only:
            print("ORDER SUMMARY:")
            print(f"  Total Orders: {order_data['total_orders']}")
            print(f"  Buy: {order_data['counts']['buy']}, Sell: {order_data['counts']['sell']}, Exit: {order_data['counts']['exit']}")
            print()
        else:
            print_order_report(order_data)
        
        print("=" * 60)
        
        return 0
        
    except Exception as e:
        print(f"EOD reporting job failed: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
